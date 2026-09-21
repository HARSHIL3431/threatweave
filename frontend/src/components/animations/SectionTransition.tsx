import { motion } from 'framer-motion'
import { ReactNode } from 'react'
import { cn } from '@/utils/cn'

interface SectionTransitionProps {
  children: ReactNode
  className?: string
  delay?: number
  staggerChildren?: number
  animateOnce?: boolean
}

const SectionTransition = ({
  children,
  className,
  delay = 0,
  staggerChildren = 0.1,
  animateOnce = true,
}: SectionTransitionProps) => {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        delayChildren: delay,
        staggerChildren,
      },
    },
  }

  return (
    <motion.div
      variants={container}
      initial="hidden"
      whileInView="show"
      viewport={{ once: animateOnce, amount: 0.1 }}
      className={cn(className)}
    >
      {children}
    </motion.div>
  )
}

// Child component for individual items
export const SectionItem = ({ children, className }: { children: ReactNode; className?: string }) => {
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { 
      opacity: 1, 
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.22, 1, 0.36, 1],
      },
    },
  }

  return (
    <motion.div variants={item} className={cn(className)}>
      {children}
    </motion.div>
  )
}

export default SectionTransition