# Cybersecurity Anomaly Detection Frontend

A modern, modular React frontend for the AI-powered network anomaly detection platform. Built with TypeScript, Vite, Tailwind CSS, and Framer Motion.

## Features

- **Interactive Landing Page**: Visual system pipeline demonstration showing the ML workflow
- **Modular Dashboard**: Real-time system monitoring and performance metrics
- **Network Flow Detection**: Submit flows for anomaly analysis with real backend integration
- **Replaceable Component Architecture**: Designed for easy UI component swapping
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Animation System**: Smooth, intentional animations with Framer Motion

## Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for utility-first styling
- **Framer Motion** for animations
- **React Query** for API state management
- **Zustand** for UI state management
- **React Router** for navigation
- **Recharts** for data visualization
- **Lucide React** for icons

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API layer with typed interfaces
│   ├── components/       # Reusable UI components
│   │   ├── ui/          # Design system primitives
│   │   ├── animations/  # Modular animation components
│   │   ├── layout/      # Layout components
│   │   └── visualization/ # Charts and visualizations
│   ├── features/        # Feature-specific components
│   │   ├── landing/     # Landing page components
│   │   ├── dashboard/   # Dashboard components
│   │   └── detection/   # Detection workflow components
│   ├── hooks/          # Custom React hooks
│   ├── pages/          # Page components
│   ├── store/          # State management
│   ├── utils/          # Utilities and helpers
│   └── styles/         # Global styles
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend running on `localhost:8000` (see backend README)

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3000 in your browser

### Building for Production

```bash
npm run build
npm run preview
```

## Component Architecture

The frontend is built with **replaceable component boundaries**:

- Each visual element is a standalone component
- Clear props interfaces with no implicit dependencies
- Business logic separated from presentation
- Animation logic encapsulated in animation components

Example: Replacing a card component only requires updating that specific component file.

## Backend Integration

The frontend connects to the FastAPI backend with:

- **Health Check**: `GET /api/v1/health`
- **Single Detection**: `POST /api/v1/detect`
- **Batch Detection**: `POST /api/v1/detect/batch`

All API calls are typed with interfaces matching the backend Pydantic schemas.

## Development Guidelines

### Adding New Components

1. Create component in appropriate directory
2. Define clear props interface
3. Keep business logic separate
4. Add TypeScript types
5. Make components replaceable

### Animation Guidelines

- Use Framer Motion for complex animations
- Keep animations subtle and intentional
- Respect reduced motion preferences
- Encapsulate animation logic in animation components

### Styling Guidelines

- Use Tailwind CSS utility classes
- Follow the design system in `tailwind.config.js`
- Keep colors consistent with the cybersecurity theme
- Ensure responsive behavior

## Testing

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Build verification
npm run build
```

## License

Proprietary - Part of the Cybersecurity Anomaly Detection Platform