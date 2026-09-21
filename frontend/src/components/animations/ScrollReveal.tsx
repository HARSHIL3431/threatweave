import { motion, useAnimation, useInView } from 'framer-motion'
import { ReactNode, useEffect, useRef } from 'react'
import { cn } from '@/utils/cn'

interface ScrollRevealProps {
  children: ReactNode
  className?: string
  delay?: number
  duration?: number
  direction?: 'up' | 'down' | 'left' | 'right'
  threshold?: number
  distance?: number
  once?: boolean
}

const ScrollReveal = ({
  children,
  className,
  delay = 0,
  duration = 0.5,
  direction = 'up',
  threshold = 0.1,
  distance = 20,
  once = true,
}: ScrollRevealProps) => {
  const ref = useRef(null)
  const isInView = useInView(ref, { once, amount: threshold })
  const controls = useAnimation()

  useEffect(() => {
    if (isInView) {
      controls.start('visible')
    }
  }, [isInView, controls])

  const directionVariants = {
    up: { y: distance, opacity: 0 },
    down: { y: -distance, opacity: 0 },
    left: { x: distance, opacity: 0 },
    right: { x: -distance, opacity: 0 },
  }

  const variants = {
    hidden: directionVariants[direction],
    visible: {
      y: 0,
      x: 0,
      opacity: 1,
      transition: {
        duration,
        delay,
        ease: [0.22, 1, 0.36, 1], // Smooth easing curve
      },
    },
  }

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={controls}
      variants={variants}
      className={cn(className)}
    >
      {children}
    </motion.div>
  )
}

export default ScrollReveal