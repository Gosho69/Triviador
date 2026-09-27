import { useAuth } from '../auth/context'
import { AuthLayout } from '../components/AuthLayout'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { FormAlert } from '../components/FormAlert'
import { required, useForm } from './useForm'

export function LoginPage() {
  const { login } = useAuth()
  const form = useForm({ username: '', password: '' })

  async function handleSubmit(event) {
    event.preventDefault()
    const validate = (values) =>
      required(values, { username: 'Enter your username.', password: 'Enter your password.' })
    // On success GuestOnly redirects to the page the user was sent here from.
    await form.submit(validate, login)
  }

  return (
    <AuthLayout title="Return to the realm" intro="Sign in to take up your banner again.">
      <form className="stack" onSubmit={handleSubmit} noValidate>
        <FormAlert errors={form.errors} />
        <Field label="Username" autoComplete="username" autoFocus error={form.errors.username} {...form.bind('username')} />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          error={form.errors.password}
          {...form.bind('password')}
        />
        <Button type="submit" pending={form.pending} pendingLabel="Signing in…">
          Sign in
        </Button>
      </form>
    </AuthLayout>
  )
}
