'use client'

import { motion } from 'framer-motion'

interface FloatingAvatarProps {
  avatar: string
  name: string
  isAI?: boolean
  delay?: number
  position?: {
    top?: string
    right?: string
    left?: string
    bottom?: string
  }
}

export default function FloatingAvatar({
  avatar,
  name,
  isAI = false,
  delay = 0,
  position
}: FloatingAvatarProps) {
  const defaultPosition = isAI 
    ? { top: '20%', right: '30%' }
    : { top: '40%', right: '20%' }

  const finalPosition = position || defaultPosition

  return (
    <motion.div
      className={`floating-avatar ${isAI ? 'ai-avatar' : 'user-avatar'}`}
      style={finalPosition}
      drag
      dragMomentum={false}
      whileDrag={{ scale: 1.1, cursor: 'grabbing' }}
      whileHover={{ scale: 1.05 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <img src={avatar} alt={name} />
    </motion.div>
  )
}

