/** Small per-browser onboarding flags. Storage can be unavailable (private mode), so every access is guarded. */

const VISITED_AGENTS = 'onboarding.visitedAgents'
const dismissedKey = (accountId: number) => `onboarding.firstSteps.dismissed.${accountId}`

function read(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

function write(key: string) {
  try {
    localStorage.setItem(key, '1')
  } catch {
    // Not persisted; the checklist simply reappears next visit.
  }
}

export const hasVisitedAgents = () => read(VISITED_AGENTS)
export const markVisitedAgents = () => write(VISITED_AGENTS)
export const isFirstStepsDismissed = (accountId: number) => read(dismissedKey(accountId))
export const dismissFirstSteps = (accountId: number) => write(dismissedKey(accountId))
