import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params

    if (!id) {
      return NextResponse.json({ error: 'User ID required' }, { status: 400 })
    }

    // Fetch matches
    const { data: matches } = await supabase
      .from('matches')
      .select('user1_id, user2_id, score')
      .or(`user1_id.eq.${id},user2_id.eq.${id}`)
      .eq('status', 'accepted')

    // Fetch group chat connections
    const { data: groupChats } = await supabase
      .from('group_chat_participants')
      .select('group_chat_id, user_id, phone_number')
      .eq('user_id', id)

    const connections: any[] = []

    // Process matches
    if (matches) {
      for (const match of matches) {
        const otherUserId = match.user1_id === id ? match.user2_id : match.user1_id
        if (otherUserId) {
          connections.push({
            user_id: otherUserId,
            connection_type: 'match',
            score: match.score
          })
        }
      }
    }

    // Process group chat connections
    if (groupChats) {
      for (const gc of groupChats) {
        const { data: participants } = await supabase
          .from('group_chat_participants')
          .select('user_id')
          .eq('group_chat_id', gc.group_chat_id)
          .neq('user_id', id)

        if (participants) {
          for (const p of participants) {
            if (p.user_id && !connections.find(c => c.user_id === p.user_id)) {
              connections.push({
                user_id: p.user_id,
                connection_type: 'group_chat'
              })
            }
          }
        }
      }
    }

    return NextResponse.json(connections)
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

