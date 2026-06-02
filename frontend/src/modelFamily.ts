import { useCallback, useEffect, useState } from 'react'

export const MODEL_FAMILY_STORAGE_KEY = 'model_family_selection'
export const MODEL_FAMILY_EVENT = 'model-family-change'

export type ModelFamily = 'xgboost' | 'random_forest' | 'both'

export const MODEL_FAMILIES: Array<{ value: ModelFamily; label: string; shortLabel: string }> = [
  { value: 'xgboost', label: 'XGBoost', shortLabel: 'XGB' },
  { value: 'random_forest', label: 'Random Forest', shortLabel: 'RF' },
  { value: 'both', label: 'Blend', shortLabel: 'Both' },
]

export function isModelFamily(value: string | null): value is ModelFamily {
  return value === 'xgboost' || value === 'random_forest' || value === 'both'
}

export function readStoredModelFamily(): ModelFamily {
  try {
    const stored = localStorage.getItem(MODEL_FAMILY_STORAGE_KEY)
    if (isModelFamily(stored)) {
      return stored
    }
  } catch {
    // Storage can fail in private or restricted browser contexts.
  }
  return 'random_forest'
}

export function writeStoredModelFamily(value: ModelFamily) {
  try {
    localStorage.setItem(MODEL_FAMILY_STORAGE_KEY, value)
  } catch {
    // Keep the in-memory state even if storage is unavailable.
  }
  window.dispatchEvent(new CustomEvent<ModelFamily>(MODEL_FAMILY_EVENT, { detail: value }))
}

export function useModelFamily() {
  const [family, setFamilyState] = useState<ModelFamily>(() => readStoredModelFamily())

  const setFamily = useCallback((value: ModelFamily) => {
    setFamilyState(value)
    writeStoredModelFamily(value)
  }, [])

  useEffect(() => {
    const handleStorage = (event: StorageEvent) => {
      if (event.key === MODEL_FAMILY_STORAGE_KEY && isModelFamily(event.newValue)) {
        setFamilyState(event.newValue)
      }
    }

    const handleLocalChange = (event: Event) => {
      const next = (event as CustomEvent<ModelFamily>).detail
      if (isModelFamily(next)) {
        setFamilyState(next)
      }
    }

    window.addEventListener('storage', handleStorage)
    window.addEventListener(MODEL_FAMILY_EVENT, handleLocalChange)
    return () => {
      window.removeEventListener('storage', handleStorage)
      window.removeEventListener(MODEL_FAMILY_EVENT, handleLocalChange)
    }
  }, [])

  return [family, setFamily] as const
}
