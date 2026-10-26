import type { components } from './schema'

export type Problem = components['schemas']['Problem']
export type FieldError = NonNullable<Problem['errors']>[number]

const TIMEOUT_MS = 15_000

/** `problem`: the API answered with an error. `network`: no answer. `timeout`: no answer in time. */
export type FailureKind = 'problem' | 'network' | 'timeout'

export class ApiError extends Error {
  readonly kind: FailureKind
  readonly status: number | undefined
  /** The contract's `Problem.code`, kept as sent so an unknown code can't be mistaken for a known one. */
  readonly code: string | undefined
  readonly fieldErrors: FieldError[]
  /** Support reference shown to the user (`X-Trace-Id`, or `trace_id` from the body). */
  readonly traceId: string | undefined

  constructor(
    kind: FailureKind,
    details: { status?: number; code?: string; fieldErrors?: FieldError[]; traceId?: string } = {},
  ) {
    super(details.code === undefined ? `API request failed: ${kind}` : `API request failed: ${details.code}`)
    this.name = 'ApiError'
    this.kind = kind
    this.status = details.status
    this.code = details.code
    this.fieldErrors = details.fieldErrors ?? []
    this.traceId = details.traceId
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  timeoutMs?: number
}

/** Sends a request to the MediTrack API and returns the parsed JSON body. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options)
  // The backend's contract test guarantees the shape; parsing again here would duplicate the generated types.
  return (await response.json()) as T
}

async function send(path: string, { method = 'GET', body, timeoutMs = TIMEOUT_MS }: RequestOptions): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => {
    controller.abort()
  }, timeoutMs)
  let response: Response
  try {
    response = await fetch(new URL(path, document.baseURI), {
      method,
      headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch {
    throw new ApiError(controller.signal.aborted ? 'timeout' : 'network')
  } finally {
    clearTimeout(timer)
  }
  if (response.ok) return response
  throw await toApiError(response)
}

async function toApiError(response: Response): Promise<ApiError> {
  const headerTraceId = response.headers.get('X-Trace-Id') ?? undefined
  const problem = await readProblem(response)
  if (import.meta.env.DEV && import.meta.env.MODE !== 'test') {
    console.warn(`MediTrack API error ${response.status}, trace ${headerTraceId ?? problem?.trace_id ?? 'none'}`)
  }
  return new ApiError('problem', {
    status: response.status,
    code: problem?.code,
    fieldErrors: problem?.errors,
    traceId: headerTraceId ?? problem?.trace_id,
  })
}

async function readProblem(response: Response): Promise<Problem | undefined> {
  try {
    const body: unknown = await response.json()
    return isProblem(body) ? body : undefined
  } catch {
    // Not JSON, e.g. an HTML error page from a proxy. The status code still says what kind of failure it was.
    return undefined
  }
}

function isProblem(body: unknown): body is Problem {
  return typeof body === 'object' && body !== null && 'code' in body && typeof body.code === 'string'
}
