# SISI - Series Interface

A minimal, elegant interface for visualizing the Series network with draggable profile cards and avatars.

## ✨ Features

- **Draggable Profile Card**: Move the profile card anywhere on screen
- **Floating Avatars**: Interactive draggable avatars for users and AI
- **Clean Design**: Minimal white canvas with smooth animations
- **Responsive**: Works beautifully on desktop and mobile
- **TypeScript**: Fully typed for better development experience

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) to see the interface.

## 📁 Project Structure

```
sisi-nextjs/
├── app/
│   ├── components/
│   │   ├── ProfileCard.tsx      # Draggable profile card component
│   │   └── FloatingAvatar.tsx   # Draggable avatar component
│   ├── api/                      # API routes for Supabase
│   │   ├── graph/
│   │   └── users/
│   ├── page.tsx                  # Main page
│   ├── layout.tsx                # Root layout
│   └── globals.css               # Global styles
├── lib/
│   └── supabase.ts               # Supabase client configuration
└── public/                       # Static assets
```

## 🎨 Components

### ProfileCard

A draggable profile card component that displays:
- User name
- Profile picture with engagement badge
- Bio section
- Social media links (LinkedIn, Instagram)

**Props:**
```typescript
interface ProfileCardProps {
  name: string
  bio: string
  avatar: string
  engagementCount?: number
  socialLinks?: {
    linkedin?: string
    instagram?: string
  }
}
```

### FloatingAvatar

A draggable avatar component for users and AI friends.

**Props:**
```typescript
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
```

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_KEY=your-supabase-key
```

## 🎯 Usage

### Basic Example

```tsx
import ProfileCard from './components/ProfileCard'
import FloatingAvatar from './components/FloatingAvatar'

export default function Home() {
  return (
    <div className="app-container">
      <ProfileCard
        name="Ola Aduloju"
        bio="Hi im ola i love to build"
        avatar="https://example.com/avatar.jpg"
        engagementCount={20}
        socialLinks={{
          linkedin: "https://linkedin.com/in/ola",
          instagram: "https://instagram.com/ola"
        }}
      />
      
      <FloatingAvatar
        avatar="https://example.com/avatar.jpg"
        name="Ola"
        isAI={false}
      />
    </div>
  )
}
```

## 🎨 Styling

The project uses CSS custom properties for easy theming:

```css
:root {
  --color-bg: #ffffff;
  --color-text: #1a1a1a;
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.1);
  --radius-lg: 16px;
}
```

## 📱 Responsive Design

- **Desktop**: Two-column layout with profile card and floating avatars
- **Tablet**: Single column with stacked layout
- **Mobile**: Optimized spacing and smaller avatars

## 🔌 API Integration

The project includes API routes for Supabase integration:

- `GET /api/users/[id]` - Get user profile
- `GET /api/users/[id]/connections` - Get user connections
- `GET /api/graph` - Get network graph data

## 🛠️ Development

### Adding New Components

1. Create component in `app/components/`
2. Export as default
3. Import and use in `page.tsx`

### Styling Guidelines

- Use CSS custom properties for colors and spacing
- Follow BEM-like naming for component classes
- Keep animations smooth and performant
- Use `framer-motion` for complex animations

## 📝 License

MIT

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
