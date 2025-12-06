# Quick Start Guide

## 🚀 Running SISI

### 1. Install Dependencies (if not already done)
```bash
cd /Users/term_/Series/sisi-nextjs
npm install
```

### 2. Set Up Environment Variables

Create `.env.local` file:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://kugbwhdljdigakumufwu.supabase.co
NEXT_PUBLIC_SUPABASE_KEY=your-anon-key-here
```

### 3. Start Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## ✨ Features

### Draggable Elements
- **Graph Nodes**: Click and drag any avatar in the connection graph
- **Profile Card**: Drag the profile card anywhere on screen
- **Zoom**: Scroll mouse wheel to zoom in/out on graph
- **Pan**: Click and drag background to pan the graph

### Interactions
- **Click Nodes**: Click any node in the graph to view that user's profile
- **Switch Tabs**: Click browser tabs to switch between users
- **Hover Effects**: Hover over nodes and cards for visual feedback

## 🎨 What's Included

✅ Browser-like header with tabs (exact Series.so match)
✅ Bookmarks bar
✅ Draggable D3.js connection graph
✅ Draggable profile cards
✅ Zoom and pan functionality
✅ Supabase API integration
✅ Responsive design

## 📝 Next Steps

1. **Connect to Real Data**: Update `.env.local` with your Supabase credentials
2. **Customize Users**: Modify `app/page.tsx` to fetch real users from API
3. **Add More Features**: Extend components with additional functionality

## 🐛 Troubleshooting

**Build Errors**: Make sure all dependencies are installed
```bash
npm install
```

**Supabase Errors**: Check your `.env.local` file has correct credentials

**Graph Not Showing**: Check browser console for D3.js errors

