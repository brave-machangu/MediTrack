import type { ButtonHTMLAttributes } from 'react'
import styles from './Button.module.css'

type Variant = 'primary' | 'secondary'

const variants: Record<Variant, string | undefined> = {
  primary: styles.primary,
  secondary: styles.secondary,
}

/** Button styling, also used for links that act as the page's main way forward. */
export function buttonClassName(variant: Variant): string {
  return `${styles.button} ${variants[variant] ?? ''}`
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }

/** Always visible text, never icon-only. `type` defaults to "button" so it can't submit a form by accident. */
export function Button({ variant = 'secondary', type = 'button', className, ...props }: Props) {
  return <button type={type} className={`${buttonClassName(variant)} ${className ?? ''}`} {...props} />
}
