import { expect, test, type Locator, type Page } from '@playwright/test'

// 1x1 transparent PNG: map tiles never depend on the internet during tests.
const BLANK_TILE = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64',
)

let problems: string[] = []
let allowed: RegExp[] = []

test.beforeEach(async ({ page }) => {
  problems = []
  allowed = []
  page.on('console', (message) => {
    if (message.type() !== 'error' && message.type() !== 'warning') return
    const text = message.text()
    if (!allowed.some((pattern) => pattern.test(text))) problems.push(`${message.type()}: ${text}`)
  })
  page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  await page.route('https://tile.openstreetmap.org/**', (route) =>
    route.fulfill({ status: 200, contentType: 'image/png', body: BLANK_TILE }),
  )
})

test.afterEach(() => {
  expect(problems, 'browser console should stay clean').toEqual([])
})

const map = (page: Page, name: string) => page.getByTestId(`map-${name}`)
const engineers = (page: Page, name: string) => map(page, name).locator('path.engineer-marker')
const tickets = (page: Page, name: string) => map(page, name).locator('.ticket-marker')

async function openApp(page: Page) {
  await page.goto('/')
  await expect(page.getByTestId('headline')).toContainText(' vs ')
  await expect(tickets(page, 'left')).toHaveCount(20)
}

async function relativeBox(marker: Locator, frame: Locator) {
  const [m, f] = await Promise.all([marker.boundingBox(), frame.boundingBox()])
  if (!m || !f) throw new Error('missing bounding box')
  return { x: Math.round(m.x - f.x), y: Math.round(m.y - f.y) }
}

test('compare tab shows both algorithms, their maps and the report card', async ({ page }) => {
  await openApp(page)

  await expect(page.getByTestId('headline')).toContainText('Hungarian vs Greedy')
  await expect(page.getByTestId('api-status')).toContainText('storage')
  for (const side of ['left', 'right']) {
    await expect(engineers(page, side)).toHaveCount(12)
    await expect(tickets(page, side)).toHaveCount(20)
    await expect(map(page, side).locator('path.map-line').first()).toBeVisible()
    for (const chip of ['coverage', 'p1', 'km', 'tight', 'unserved', 'objective']) {
      await expect(page.getByTestId(`panel-${side}`).getByTestId(`chip-${chip}`)).toBeVisible()
    }
  }
  // Greedy leaves tickets unserved on this seed: they are drawn with a dashed outline.
  await expect(tickets(page, 'left').and(page.locator('.unassigned')).first()).toBeAttached()

  const table = page.getByTestId('metrics-table')
  await expect(table.getByRole('columnheader')).toHaveText(['Metric', 'Greedy', 'Hungarian', 'Regret'])
  await expect(table.locator('td.best').first()).toBeVisible()
  await expect(page.getByTestId('metrics-chart').locator('.recharts-bar-rectangle').first()).toBeVisible()
})

test('both maps open fitted to the whole scenario', async ({ page }) => {
  await openApp(page)
  for (const side of ['left', 'right']) {
    const frame = await map(page, side).boundingBox()
    if (!frame) throw new Error('map has no size')
    const inside = await tickets(page, side).evaluateAll(
      (markers, box) =>
        markers.filter((m) => {
          const r = m.getBoundingClientRect()
          return r.left >= box.x && r.right <= box.x + box.width && r.top >= box.y && r.bottom <= box.y + box.height
        }).length,
      frame,
    )
    expect(inside, `${side} map shows every ticket`).toBe(20)
  }
})

test('maps stay in sync when one is zoomed', async ({ page }) => {
  await openApp(page)
  await map(page, 'left').locator('.leaflet-control-zoom-in').click()
  await expect
    .poll(async () => {
      const left = await relativeBox(tickets(page, 'left').first(), map(page, 'left'))
      const right = await relativeBox(tickets(page, 'right').first(), map(page, 'right'))
      return Math.abs(left.x - right.x) + Math.abs(left.y - right.y)
    })
    .toBeLessThanOrEqual(2)
})

test('clicking a ticket explains the decision of both algorithms', async ({ page }) => {
  await openApp(page)
  const first = tickets(page, 'left').first()
  const ticketId = await first.getAttribute('data-ticket-id')
  await first.dispatchEvent('click')

  const panel = page.getByTestId('explanation')
  await expect(panel.getByRole('heading', { name: `Why? ${ticketId}` })).toBeVisible()
  for (const algorithm of ['greedy', 'hungarian']) {
    await expect(panel.getByTestId(`decision-${algorithm}`)).toContainText(/→ E\d+|Left unassigned/)
  }
  await expect(tickets(page, 'right').and(page.locator('.selected'))).toHaveCount(1)

  await panel.getByRole('button', { name: 'Clear' }).click()
  await expect(panel.getByRole('heading', { name: 'Why? Click any ticket or line' })).toBeVisible()
})

test('changing the engineer count regenerates the scenario on both maps', async ({ page }) => {
  await openApp(page)
  await page.getByLabel('Engineers', { exact: true }).fill('6')
  await expect(engineers(page, 'left')).toHaveCount(6)
  await expect(engineers(page, 'right')).toHaveCount(6)
  await expect(tickets(page, 'left')).toHaveCount(20)
  await expect(page.getByTestId('headline')).toContainText(' vs ')
})

test('switching the left algorithm updates the headline', async ({ page }) => {
  await openApp(page)
  await page.getByLabel('Left algorithm').selectOption('regret')
  await expect(page.getByTestId('headline')).toContainText('Regret')
})

test('the scenario can be edited on the map and reset', async ({ page }) => {
  await openApp(page)
  await page.getByRole('button', { name: 'Add engineer' }).click()
  // fitBounds keeps a 28 px margin, so the bottom-left corner is empty map.
  await map(page, 'left').click({ position: { x: 14, y: 326 } })
  await expect(engineers(page, 'left')).toHaveCount(13)
  await expect(engineers(page, 'right')).toHaveCount(13)
  await expect(page.getByText('edited', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'Delete ticket' }).click()
  await tickets(page, 'left').first().dispatchEvent('click')
  await expect(tickets(page, 'left')).toHaveCount(19)

  await page.getByRole('button', { name: 'Reset edits' }).click()
  await expect(engineers(page, 'left')).toHaveCount(12)
  await expect(tickets(page, 'left')).toHaveCount(20)
})

test('how it works replays the five steps', async ({ page }) => {
  await openApp(page)
  await page.getByRole('tab', { name: 'How it works' }).click()
  await expect(page.getByTestId('step-1')).toBeVisible()
  await expect(map(page, 'how-scenario').locator('.ticket-marker')).toHaveCount(20)

  await page.getByRole('tab', { name: '2 Hard filter' }).click()
  await expect(page.getByTestId('filter-summary')).toContainText(/\d+ of 12 engineers may take T\d+/)
  await expect(page.getByTestId('filter-list').locator('li')).toHaveCount(12)

  await page.getByRole('tab', { name: '3 Cost grid' }).click()
  const grid = page.getByTestId('cost-grid')
  await expect(grid.locator('td.cell')).toHaveCount(20 * 12)
  await grid.locator('td.cell.allowed').first().hover()
  await expect(page.getByTestId('cost-readout')).toContainText('cost')

  await page.getByRole('tab', { name: '4 Assign' }).click()
  await expect(page.getByTestId('pick-counter')).toContainText('pick 0 of')
  await page.getByRole('button', { name: 'Next ▶' }).click()
  await page.getByRole('button', { name: 'Next ▶' }).click()
  await expect(page.getByTestId('pick-counter')).toContainText('pick 2 of')
  await expect(page.getByTestId('assign-grid-left').locator('td.current')).toHaveCount(1)
  await expect(page.getByTestId('assign-grid-right').locator('td.chosen').first()).toBeVisible()

  await page.getByRole('tab', { name: '5 Report card' }).click()
  await expect(page.getByTestId('step-5')).toContainText('vs')

  await page.getByRole('tab', { name: '1 Scenario' }).click()
  await page.getByTestId('play').click()
  await expect(page.getByTestId('step-2')).toBeVisible({ timeout: 6_000 })
  await page.getByTestId('play').click()

  await page.getByRole('tab', { name: '5 Report card' }).click()
  await page.getByRole('button', { name: 'Open the Experiment tab' }).click()
  await expect(page.getByTestId('sweep-form')).toBeVisible()
})

test('experiment tab runs the scarcity sweep', async ({ page }) => {
  await openApp(page)
  await page.getByRole('tab', { name: 'Experiment' }).click()
  await page.getByLabel('Tickets').fill('12')
  await page.getByLabel('Seeds per ratio').fill('3')
  await page.getByRole('button', { name: 'Run sweep' }).click()

  await expect(page.getByTestId('sweep-findings').locator('li')).toHaveCount(4)
  const rows = page.getByTestId('sweep-table').locator('tbody tr')
  await expect(rows).toHaveCount(6 * 3)
  const hungarianRows = rows.filter({ hasText: 'Hungarian' })
  await expect(hungarianRows).toHaveCount(6)
  for (const row of await hungarianRows.all()) {
    await expect(row.locator('td').nth(3)).toHaveText('0.0%')
  }
  await expect(page.getByTestId('sweep-gap-chart').locator('.recharts-line')).toHaveCount(3)
})

test('the sweep form rejects bad ratios before calling the API', async ({ page }) => {
  await openApp(page)
  await page.getByRole('tab', { name: 'Experiment' }).click()
  await page.getByLabel('Engineers per ticket').fill('0.5, -1')
  await expect(page.getByText('Enter positive numbers separated by commas.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Run sweep' })).toBeDisabled()
})

test('API errors show inline next to the panel that failed', async ({ page }) => {
  allowed = [/status of 422/]
  await page.route('**/api/allocate', (route) =>
    route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({
        error: { code: 'VALIDATION_ERROR', message: 'algorithms.0: Input should be greedy', details: {} },
      }),
    }),
  )
  await page.goto('/')
  await expect(page.getByTestId('panel-left').getByTestId('error-note')).toContainText('VALIDATION_ERROR')
  await expect(page.getByTestId('panel-right').getByTestId('error-note')).toContainText(
    'algorithms.0: Input should be greedy',
  )
  // The scenario still draws: one failing call never blanks the page.
  await expect(tickets(page, 'left')).toHaveCount(20)
})

test('markers and lines still draw when map tiles are offline', async ({ page }) => {
  allowed = [/Failed to load resource/]
  await page.unroute('https://tile.openstreetmap.org/**')
  await page.route('https://tile.openstreetmap.org/**', (route) => route.abort())
  await openApp(page)
  await expect(engineers(page, 'right')).toHaveCount(12)
  await expect(map(page, 'right').locator('path.map-line').first()).toBeVisible()
})
