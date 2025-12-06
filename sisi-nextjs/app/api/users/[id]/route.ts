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

    // Fetch user from Supabase
    const { data, error } = await supabase
      .from('sessions')
      .select('user_id, name, school, age, hobbies')
      .eq('user_id', id)
      .single()

    if (error) {
      console.error('Supabase error:', error)
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    // Format response
    const profile = {
      id: data.user_id,
      name: data.name || 'Unknown',
      bio: `Hi, I'm ${data.name || 'a user'}. ${data.hobbies ? `I love ${data.hobbies}` : ''}`,
      avatar: `https://i.pravatar.cc/400?img=${id.charCodeAt(0) % 70}`,
      school: data.school,
      age: data.age,
      hobbies: data.hobbies
    }

    return NextResponse.json(profile)
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

