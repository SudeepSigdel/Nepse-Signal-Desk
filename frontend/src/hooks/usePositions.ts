import { useUserData } from '../context/UserDataContext'

/** Holdings are now account-persisted (see UserDataContext); this keeps the old call shape. */
export function usePositions() {
  const { holdings, addHolding, removeHolding } = useUserData()
  return { holdings, addHolding, removeHolding }
}
