import { expect, test, type Page } from '@playwright/test'

// Writes the README images to <repo>/docs/screenshots. Real OpenStreetMap tiles are used,
// so the maps look like the app does for a reviewer.
const OUT = '../docs/screenshots'

async function settle(page: Page) {
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(500)
}

test('compare tab', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('headline')).toContainText(' vs ')
  await expect(page.getByTestId('map-left').locator('.ticket-marker')).toHaveCount(20)
  const ticket = page.getByTestId('map-left').locator('.ticket-marker[data-priority="P1"]').first()
  await ticket.dispatchEvent('click')
  await settle(page)
  await page.screenshot({ path: `${OUT}/compare.png` })
})

test('how it works tab', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('headline')).toContainText(' vs ')
  await page.getByRole('tab', { name: 'How it works' }).click()
  await page.getByRole('tab', { name: '4 Assign' }).click()
  for (let i = 0; i < 6; i += 1) await page.getByRole('button', { name: 'Next ▶' }).click()
  await expect(page.getByTestId('pick-counter')).toContainText('pick 6 of')
  await settle(page)
  await page.screenshot({ path: `${OUT}/how-it-works.png` })
})

test('experiment tab', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('tab', { name: 'Experiment' }).click()
  await page.getByRole('button', { name: 'Run sweep' }).click()
  await expect(page.getByTestId('sweep-findings').locator('li')).toHaveCount(4)
  await settle(page)
  await page.screenshot({ path: `${OUT}/experiment.png` })
})
