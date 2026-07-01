import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Landing point after a Google OAuth redirect; the backend appends ?token=... */
export function AuthCallbackPage() {
  const { applyToken } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState(false)
  const ranRef = useRef(false)

  useEffect(() => {
    if (ranRef.current) return
    ranRef.current = true

    const token = searchParams.get('token')
    if (!token) {
      setError(true)
      return
    }
    applyToken(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setError(true))
  }, [applyToken, navigate, searchParams])

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center p-4 text-center">
      {error ? (
        <>
          <p className="text-sm text-rose-500">Google sign-in failed. Please try again.</p>
        </>
      ) : (
        <p className="text-sm text-zinc-400 dark:text-zinc-500">Signing you in…</p>
      )}
    </div>
  )
}
