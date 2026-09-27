import { useState } from 'react'
import { ApiError } from '../api/client'

// Shared form state: values, server/client errors, and a pending flag.
export function useForm(initialValues) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [pending, setPending] = useState(false)

  function bind(name) {
    return {
      name,
      value: values[name],
      onChange: (event) => {
        const { value } = event.target
        setValues((current) => ({ ...current, [name]: value }))
        setErrors((current) => (current[name] ? { ...current, [name]: undefined } : current))
      },
    }
  }

  async function submit(validate, action) {
    const clientErrors = validate(values)
    if (Object.keys(clientErrors).length > 0) {
      setErrors(clientErrors)
      return false
    }
    setPending(true)
    setErrors({})
    try {
      await action(values)
      return true
    } catch (error) {
      setErrors(error instanceof ApiError ? error.errors : { non_field_errors: [String(error)] })
      return false
    } finally {
      setPending(false)
    }
  }

  return { values, setValues, errors, setErrors, pending, bind, submit }
}

export function required(values, messages) {
  const errors = {}
  for (const [name, message] of Object.entries(messages)) {
    if (!String(values[name] ?? '').trim()) errors[name] = [message]
  }
  return errors
}
