'use client'

import ProfileCard from './components/ProfileCard'
import FloatingAvatar from './components/FloatingAvatar'

// Mock data - replace with API calls later
const user = {
  id: 'ola',
  name: 'Ola Aduloju',
  bio: 'Hi im ola i love to build',
  avatar: '/placeholder-user.svg', // Placeholder image
  engagementCount: 20,
  socialLinks: {
    linkedin: '#',
    instagram: '#'
  }
}

const aiFriend = {
  id: 'zara',
  name: 'Zara',
  avatar: '/placeholder-ai.svg', // Placeholder image
  isAI: true
}

export default function Home() {
  return (
    <div className="app-container">
      <div className="main-content">
        {/* Profile Card - Left Side */}
        <ProfileCard
          name={user.name}
          bio={user.bio}
          avatar={user.avatar}
          engagementCount={user.engagementCount}
          socialLinks={user.socialLinks}
        />

        {/* Floating Avatars - Right Side */}
        <div className="floating-avatars">
          <FloatingAvatar
            avatar={aiFriend.avatar}
            name={aiFriend.name}
            isAI={true}
            delay={0.2}
          />
          <FloatingAvatar
            avatar={user.avatar}
            name={user.name}
            isAI={false}
            delay={0.4}
          />
        </div>
      </div>

      {/* Yellow Asterisk Icon - Bottom Right */}
      <div className="asterisk-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#FFD700">
          <path d="M12 2L13.09 8.26L20 9L13.09 9.74L12 16L10.91 9.74L4 9L10.91 8.26L12 2Z"/>
        </svg>
      </div>
    </div>
  )
}
