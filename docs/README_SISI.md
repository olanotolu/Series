# SISI - Series Interface

A clean, modern UI inspired by Series.so that displays user profiles and connection graphs.

## Features

- **Profile Cards**: Beautiful profile display with avatar, bio, and social links
- **Connection Graph**: Visual representation of network connections
- **Browser-like Interface**: Mimics the Series.so browser experience
- **Responsive Design**: Works on desktop and mobile devices
- **AI Friend Badge**: Special styling for AI friend profiles

## Usage

Simply open `sisi.html` in your web browser:

```bash
open sisi.html
# or
python3 -m http.server 8000
# Then visit http://localhost:8000/sisi.html
```

## Customization

### Change Profile Data

Edit the HTML to update:
- Profile name
- Bio text
- Avatar images (currently using placeholder avatars from pravatar.cc)
- Social media links

### Styling

All styles are in the `<style>` section of the HTML file. Key customization points:
- Colors: Update hex values for theme colors
- Spacing: Adjust padding and margins
- Fonts: Change font-family for different typography

## Structure

```
sisi.html
├── Browser Header (tabs)
├── Bookmarks Bar
└── Main Content
    ├── Connection Graph (left)
    └── Profile Card (right)
```

## Next Steps

To make this interactive with your Series backend:

1. **Connect to API**: Add JavaScript to fetch real user data
2. **Dynamic Profiles**: Load profiles from your database
3. **Real Connections**: Show actual network connections
4. **Authentication**: Add login/session management
5. **Real-time Updates**: Use WebSockets for live updates

## Example API Integration

```javascript
// Fetch user profile
async function loadProfile(userId) {
    const response = await fetch(`/api/users/${userId}`);
    const profile = await response.json();
    updateProfileCard(profile);
}

// Update profile card
function updateProfileCard(profile) {
    document.querySelector('.profile-name').textContent = profile.name;
    document.querySelector('.bio-text').textContent = profile.bio;
    document.querySelector('.profile-picture').src = profile.avatar_url;
}
```

