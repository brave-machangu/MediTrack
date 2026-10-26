import { delay, http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { copy } from '../copy'
import { patientA, TRACE_ID } from '../mocks/data'
import { problem } from '../mocks/handlers'
import { server } from '../mocks/server'
import { ApiError, request } from './client'
import { errorMessage } from './errors'

const url = '/api/v1/patients/x'

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  const error: unknown = await promise.then(
    () => undefined,
    (reason: unknown) => reason,
  )
  if (!(error instanceof ApiError)) throw new Error('expected the request to fail with an ApiError')
  return error
}

describe('request', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns the JSON body of a successful response', async () => {
    server.use(http.get(url, () => HttpResponse.json(patientA)))
    await expect(request(url)).resolves.toEqual(patientA)
  })

  it('turns a problem+json response into its code, field errors and support reference', async () => {
    server.use(
      http.get(url, () =>
        HttpResponse.json(
          {
            title: 'Invalid',
            status: 422,
            code: 'VALIDATION_ERROR',
            errors: [{ field: 'timezone', message: 'Not a valid IANA timezone' }],
            trace_id: TRACE_ID,
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json', 'X-Trace-Id': TRACE_ID } },
        ),
      ),
    )
    const error = await failure(request(url))
    expect(error).toMatchObject({ kind: 'problem', status: 422, code: 'VALIDATION_ERROR', traceId: TRACE_ID })
    expect(error.fieldErrors).toEqual([{ field: 'timezone', message: 'Not a valid IANA timezone' }])
  })

  it('falls back to the body trace_id when the X-Trace-Id header is missing', async () => {
    server.use(
      http.get(url, () =>
        HttpResponse.json({ title: 'Boom', status: 500, code: 'INTERNAL_ERROR', trace_id: 'abc123' }, { status: 500 }),
      ),
    )
    expect((await failure(request(url))).traceId).toBe('abc123')
  })

  it('handles an error response that is not JSON by its status code', async () => {
    server.use(http.get(url, () => new HttpResponse('<h1>Bad gateway</h1>', { status: 503 })))
    const error = await failure(request(url))
    expect(error).toMatchObject({ kind: 'problem', status: 503, code: undefined })
    expect(errorMessage(error)).toBe(copy.error.SERVICE_UNAVAILABLE)
  })

  it('reports a network failure without a support reference', async () => {
    server.use(http.get(url, () => HttpResponse.error()))
    const error = await failure(request(url))
    expect(error).toMatchObject({ kind: 'network', traceId: undefined })
    expect(errorMessage(error)).toBe(copy.error.network)
  })

  it('gives up when the API does not answer in time', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    server.use(
      http.get(url, async () => {
        await delay('infinite')
        return HttpResponse.json({})
      }),
    )
    const pending = failure(request(url, { timeoutMs: 1000 }))
    await vi.advanceTimersByTimeAsync(1000)
    const error = await pending
    expect(error.kind).toBe('timeout')
    expect(errorMessage(error)).toBe(copy.error.timeout)
  })
})

describe('errorMessage', () => {
  it('maps a known code to its copy', async () => {
    server.use(http.get(url, () => problem(409, 'PATIENT_HAS_LOGS', 'Patient has logs')))
    expect(errorMessage(await failure(request(url)))).toBe(copy.error.PATIENT_HAS_LOGS)
  })

  it('shows the generic message for METHOD_NOT_ALLOWED, which only a bug could cause', async () => {
    server.use(http.get(url, () => problem(405, 'METHOD_NOT_ALLOWED', 'Method not allowed')))
    expect(errorMessage(await failure(request(url)))).toBe(copy.error.INTERNAL_ERROR)
  })

  it('treats a code the contract does not define as an internal error', async () => {
    server.use(
      http.get(url, () => HttpResponse.json({ title: 'New', status: 409, code: 'SOMETHING_NEW' }, { status: 409 })),
    )
    expect(errorMessage(await failure(request(url)))).toBe(copy.error.INTERNAL_ERROR)
  })
})
