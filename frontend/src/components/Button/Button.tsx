import type { ComponentProps } from 'react'
import styles from './Button.module.css'

type Variant = 'primary' | 'secondary' | 'quiet'

const variants: Record<Variant, string | undefined> = {
  primary: styles.primary,
  secondary: styles.secondary,
  quiet: styles.quiet,
}

/** Button styling, also used for links that act as the page's main way forward. */
export function buttonClassName(variant: Variant): string {
  return `${styles.button} ${variants[variant] ?? ''}`
}

// React 19 passes `ref` as an ordinary prop, so it reaches the <button> through the spread.
type Props = ComponentProps<'button'> & { variant?: Variant }

/** Always visible text, never icon-only. `type` defaults to "button" so it can't submit a form by accident. */
export function Button({ variant = 'secondary', type = 'button', className, ...props }: Props) {
  return <button type={type} className={`${buttonClassName(variant)} ${className ?? ''}`} {...props} />
}
