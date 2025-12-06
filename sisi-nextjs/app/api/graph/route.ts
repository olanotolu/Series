import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const centerUserId = searchParams.get('center_user_id')

    // Fetch all users with completed profiles
    const { data: users } = await supabase
      .from('sessions')
      .select('user_id, name')
      .eq('onboarding_complete', true)
      .limit(50)

    if (!users || users.length === 0) {
      return NextResponse.json({ nodes: [], links: [] })
    }

    // Create nodes
    const nodes = users.map((user, index) => ({
      id: user.user_id,
      name: user.name || 'Unknown',
      avatar: `https://i.pravatar.cc/150?img=${index % 70}`,
      isAI: false
    }))

    // Add AI friend node
    nodes.push({
      id: 'zara',
      name: 'Zara',
      avatar: 'https://i.pravatar.cc/150?img=47',
      isAI: true
    })

    // Fetch matches to create links
    const { data: matches } = await supabase
      .from('matches')
      .select('user1_id, user2_id, score')
      .eq('status', 'accepted')
      .limit(100)

    const links: any[] = []

    if (matches) {
      for (const match of matches) {
        // Link AI to first user
        if (nodes.find(n => n.id === match.user1_id)) {
          links.push({
            source: 'zara',
            target: match.user1_id
          })
        }
        // Link matched users
        if (match.user1_id && match.user2_id) {
          links.push({
            source: match.user1_id,
            target: match.user2_id
          })
        }
      }
    }

    // If no matches, create default link
    if (links.length === 0 && nodes.length > 1) {
      links.push({
        source: 'zara',
        target: nodes[0].id
      })
    }

    return NextResponse.json({ nodes, links })
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

