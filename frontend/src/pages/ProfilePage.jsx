import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/context'
import { AvatarPicker } from '../components/AvatarPicker'
import { Button } from '../components/Button'
import { Field } from '../components/Field'
import { FormAlert } from '../components/FormAlert'
import { Frame } from '../components/Frame'
import { KnightCrest } from '../components/KnightCrest'
import { NightSky } from '../components/NightSky'
import { Wordmark } from '../components/Wordmark'
import { knightFor } from '../knights'
import { required, useForm } from './useForm'

export function ProfilePage() {
  const { user } = useAuth()
  // Accounts made with `createsuperuser` have no profile until one is added in the admin.
  return user.profile ? <ProfileEditor user={user} /> : <MissingProfile />
}

function MissingProfile() {
  const { logout } = useAuth()
  return (
    <div className="loading-screen" role="alert">
      <p>This account has no player profile.</p>
      <p className="loading-screen__detail">Add a profile for it in the Django admin, or sign in with a player account.</p>
      <Button variant="ghost" onClick={() => logout()}>
        Log out
      </Button>
    </div>
  )
}

function ProfileEditor({ user }) {
  const { logout, updateProfile } = useAuth()
  const navigate = useNavigate()
  const { profile } = user
  const form = useForm({ nickname: profile.nickname, avatar_key: profile.avatar_key })
  const [sealed, setSealed] = useState(false)
  const [leaving, setLeaving] = useState(false)

  const dirty = form.values.nickname !== profile.nickname || form.values.avatar_key !== profile.avatar_key
  const previewKnight = knightFor(form.values.avatar_key)
  const previewName = form.values.nickname.trim() || profile.nickname

  async function handleSubmit(event) {
    event.preventDefault()
    const validate = (values) => required(values, { nickname: 'Your nickname cannot be empty.' })
    const ok = await form.submit(validate, async (values) => {
      const updated = await updateProfile({ nickname: values.nickname.trim(), avatar_key: values.avatar_key })
      form.setValues({ nickname: updated.profile.nickname, avatar_key: updated.profile.avatar_key })
    })
    setSealed(ok)
  }

  async function handleLogout() {
    setLeaving(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch (error) {
      form.setErrors(error.errors ?? { non_field_errors: [String(error)] })
      setLeaving(false)
    }
  }

  function handleEdit(apply) {
    setSealed(false)
    apply()
  }

  return (
    <div className="profile-screen" data-colour={previewKnight.colour}>
      <NightSky />
      <header className="topbar">
        <Wordmark size="small" />
        <div className="topbar__player">
          <KnightCrest avatarKey={profile.avatar_key} size={30} title="" />
          <span className="topbar__name">{profile.nickname}</span>
          <Button variant="ghost" onClick={handleLogout} pending={leaving} pendingLabel="Logging out…">
            Log out
          </Button>
        </div>
      </header>

      <main className="profile">
        <section className="banner" aria-labelledby="banner-name">
          <div className="banner__cloth">
            <KnightCrest avatarKey={previewKnight.key} size={128} />
            <h1 id="banner-name" className="banner__name">
              {previewName}
            </h1>
            <p className="banner__title">{previewKnight.name}</p>
            {dirty && <p className="banner__preview">Preview · not saved yet</p>}
          </div>
          <dl className="ledger">
            <div>
              <dt>Username</dt>
              <dd>{user.username}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email}</dd>
            </div>
          </dl>
        </section>

        <Frame className="profile__panel" aria-labelledby="edit-title">
          <h2 id="edit-title" className="panel-title">
            Your banner
          </h2>
          <p className="panel-intro">Pick the name and knight other players will see.</p>
          <form className="stack" onSubmit={handleSubmit} noValidate>
            <FormAlert errors={form.errors} />
            <Field
              label="Nickname"
              maxLength={30}
              autoComplete="nickname"
              error={form.errors.nickname}
              hint="Max 30 characters. Must be unique."
              {...form.bind('nickname')}
              onChange={(event) => handleEdit(() => form.bind('nickname').onChange(event))}
            />
            <AvatarPicker
              value={form.values.avatar_key}
              error={form.errors.avatar_key}
              onChange={(key) => handleEdit(() => form.setValues((current) => ({ ...current, avatar_key: key })))}
            />
            <div className="profile__actions">
              <Button type="submit" pending={form.pending} pendingLabel="Saving…" disabled={!dirty}>
                Save changes
              </Button>
              <div className="seal-slot" aria-live="polite">
                {sealed && !dirty && (
                  <p className="seal">
                    <svg className="seal__wax" viewBox="0 0 40 40" aria-hidden="true">
                      <path d="M20 2l4 3 5-1 2 5 5 2-1 5 3 4-3 4 1 5-5 2-2 5-5-1-4 3-4-3-5 1-2-5-5-2 1-5-3-4 3-4-1-5 5-2 2-5 5 1Z" />
                      <path d="M13 20.5l4.5 4.5L27 15.5" className="seal__mark" />
                    </svg>
                    Changes sealed.
                  </p>
                )}
              </div>
            </div>
          </form>
        </Frame>
      </main>
    </div>
  )
}
