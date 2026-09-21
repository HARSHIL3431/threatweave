import { useEffect, useState } from 'react'

// Persist a local UI setting to localStorage. Used for settings that are not
// connected to the backend yet, so user preference survives a refresh while
// staying clearly labelled as a "Local / Demo Setting".
export function usePersistentState<T>(
  key: string,
  initialValue: T
): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    try {
      const stored = window.localStorage.getItem(key)
      if (stored !== null) {
        return JSON.parse(stored) as T
      }
    } catch {
      // Ignore corrupt or unavailable storage and fall back to the default.
    }
    return initialValue
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Storage may be unavailable (private mode / quota); state still works.
    }
  }, [key, value])

  return [value, setValue]
}