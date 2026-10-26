import { useEffect, useState } from 'react'

/** The current time. The only place the app reads the clock (AGENTS.md rule 6), so tests can fix it. */
export function now(): Date {
  return new Date()
}

/** The current time, refreshed every minute so time-based display (open log windows) keeps up without a reload. */
export function useNow(intervalMs = 60_000): Date {
  const [current, setCurrent] = useState(now)
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent(now())
    }, intervalMs)
    return () => {
      clearInterval(timer)
    }
  }, [intervalMs])
  return current
}
