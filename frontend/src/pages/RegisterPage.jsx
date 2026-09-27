import { useAuth } from '../auth/context'
import { AuthLayout } from '../components/AuthLayout'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { FormAlert } from '../components/FormAlert'
import { required, useForm } from './useForm'

const EMPTY = { username: '', email: '', nickname: '', password: '', password_confirm: '' }

function validate(values) {
  const errors = required(values, {
    username: 'Choose a username.',
    email: 'Enter your email address.',
    nickname: 'Choose a nickname other players will see.',
    password: 'Choose a password.',
    password_confirm: 'Repeat your password.',
  })
  if (!errors.password_confirm && values.password !== values.password_confirm) {
    errors.password_confirm = ['Passwords do not match.']
  }
  return errors
}

export function RegisterPage() {
  const { register } = useAuth()
  const form = useForm(EMPTY)

  async function handleSubmit(event) {
    event.preventDefault()
    // On success GuestOnly redirects to the profile.
    await form.submit(validate, register)
  }

  return (
    <AuthLayout title="Join the realm" intro="Create your account and raise your banner.">
      <form className="stack" onSubmit={handleSubmit} noValidate>
        <FormAlert errors={form.errors} />
        <div className="field-row">
          <Field label="Username" autoComplete="username" autoFocus error={form.errors.username} {...form.bind('username')} />
          <Field
            label="Nickname"
            hint="Shown to other players. Max 30 characters."
            maxLength={30}
            autoComplete="nickname"
            error={form.errors.nickname}
            {...form.bind('nickname')}
          />
        </div>
        <Field label="Email" type="email" autoComplete="email" error={form.errors.email} {...form.bind('email')} />
        <div className="field-row">
          <Field
            label="Password"
            type="password"
            autoComplete="new-password"
            error={form.errors.password}
            {...form.bind('password')}
          />
          <Field
            label="Repeat password"
            type="password"
            autoComplete="new-password"
            error={form.errors.password_confirm}
            {...form.bind('password_confirm')}
          />
        </div>
        <Button type="submit" pending={form.pending} pendingLabel="Creating account…">
          Create account
        </Button>
      </form>
    </AuthLayout>
  )
}
