// Friendly names for the types generated from the API's OpenAPI schema (`npm run gen:types`).
import type { components } from './types'

type Schemas = components['schemas']

export type Meta = Schemas['MetaResponse']
export type Scenario = Schemas['ScenarioSchema']
export type Engineer = Schemas['EngineerSchema']
export type Ticket = Schemas['TicketSchema']
export type GenerateRequest = Schemas['GenerateRequest']
export type AllocateRequest = Schemas['AllocateRequest']
export type AllocateResponse = Schemas['AllocateResponse']
export type AllocationConfig = Schemas['AllocationConfigSchema']
export type AllocationResult = Schemas['AllocationResultSchema']
export type Assignment = Schemas['AssignmentSchema']
export type Unassigned = Schemas['UnassignedSchema']
export type Metrics = Schemas['MetricsSchema']
export type RunnerUp = Schemas['RunnerUpSchema']
export type Trace = Schemas['TraceSchema']
export type SweepRequest = Schemas['SweepRequest']
export type SweepResponse = Schemas['SweepResponse']
export type SweepPoint = Schemas['SweepPointSchema']
export type ErrorEnvelope = Schemas['ErrorEnvelope']

export type AlgorithmName = AllocationResult['algorithm']
export type FaultType = Ticket['fault_type']
export type Priority = Ticket['priority']
export type Results = Partial<Record<AlgorithmName, AllocationResult>>
