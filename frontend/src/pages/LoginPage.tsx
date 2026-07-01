import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { googleLoginUrl } from '../lib/api'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const from = (location.state as { from?: Location })?.from?.pathname ?? '/'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch {
      setError('Incorrect email or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center p-4 sm:p-6">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Log in</h1>
      <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
        Access your watchlist and portfolio from any device.
      </p>

      <form onSubmit={handleSubmit} className="mt-5 space-y-3">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-zinc-200 bg-white px-2.5 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-zinc-200 bg-white px-2.5 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
        </label>

        {error && <p className="text-xs text-rose-500">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>

      <div className="my-4 flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
        or
        <div className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
      </div>

      <a
        href={googleLoginUrl()}
        className="w-full rounded-md border border-zinc-200 px-3 py-1.5 text-center text-sm font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
      >
        Continue with Google
      </a>

      <p className="mt-5 text-center text-xs text-zinc-500 dark:text-zinc-400">
        Don't have an account?{' '}
        <Link to="/signup" className="font-medium text-zinc-900 hover:underline dark:text-zinc-100">
          Sign up
        </Link>
      </p>
    </div>
  )
}
