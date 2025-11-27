# Credit Engine 2.0 - Frontend

React + Material UI frontend for the Credit Engine 2.0 dispute letter generator.

## Prerequisites

- Node.js 18+
- npm or yarn
- Backend server running on `http://localhost:8000`

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm start
```

The app will open at `http://localhost:3000`

## Project Structure

```
src/
├── api/                    # API client and service modules
│   ├── apiClient.js        # Axios instance with interceptors
│   ├── reportApi.js        # Report upload/retrieval
│   ├── auditApi.js         # Audit results
│   └── letterApi.js        # Letter generation
│
├── components/             # Reusable UI components
│   ├── FileUploader.jsx    # Drag-and-drop file upload
│   ├── ReportSummary.jsx   # Report statistics display
│   ├── ViolationList.jsx   # Violation list with grouping
│   ├── ViolationToggle.jsx # Individual violation card
│   ├── ToneSelector.jsx    # Tone and strategy selection
│   └── LetterPreview.jsx   # Letter display with download
│
├── pages/                  # Route pages
│   ├── UploadPage.jsx      # /upload - File upload
│   ├── AuditPage.jsx       # /audit/:reportId - Violation review
│   └── LetterPage.jsx      # /letter/:reportId - Letter generation
│
├── state/                  # Zustand state stores
│   ├── reportStore.js      # Report state management
│   ├── violationStore.js   # Violation selection state
│   └── uiStore.js          # UI state (tone, letter)
│
├── utils/                  # Utility functions
│   ├── formatViolation.js  # Violation display formatting
│   ├── formatLetter.js     # Letter formatting/download
│   └── formatDate.js       # Date formatting
│
└── App.js                  # Main app with routing
```

## Routes

| Route | Page | Description |
|-------|------|-------------|
| `/upload` | UploadPage | Upload credit report file |
| `/audit/:reportId` | AuditPage | Review and select violations |
| `/letter/:reportId` | LetterPage | Generate and download letter |

## Environment Variables

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

## User Flow

1. **Upload** - User uploads HTML credit report
2. **Review** - View detected violations, select which to dispute
3. **Customize** - Choose letter tone and grouping strategy
4. **Generate** - Create dispute letter
5. **Download** - Download letter as text file

## Available Scripts

```bash
npm start       # Start dev server
npm run build   # Production build
npm test        # Run tests
```

## Backend Integration

The frontend expects these backend endpoints:

- `POST /reports/upload` - Upload credit report
- `GET /reports/{id}/audit` - Get audit results
- `POST /letters/generate` - Generate dispute letter
- `GET /letters/tones` - Get available tones

## Key Features

- Drag-and-drop file upload
- Real-time violation detection display
- Violation selection with toggle controls
- 4 letter tones (formal, assertive, conversational, narrative)
- 3 grouping strategies (by type, by account, by bureau)
- Letter preview with print/copy/download
- Mobile-responsive Material UI design
