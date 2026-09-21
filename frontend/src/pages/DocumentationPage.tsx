import { BookOpen, CheckCircle2, ChevronRight } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import { docSections, integrationStatusLegend } from '@/data/mock/documentation'
import type { DocStatusVariant } from '@/data/mock/types'

// Maps documentation status labels to <Badge> variants. "IMPLEMENTED" and
// "VERIFIED" are green; anything with pending integration is amber; DEMO is blue.
const statusVariant = (label: string): DocStatusVariant => {
  if (label.startsWith('IMPLEMENTED') || label.startsWith('VERIFIED')) return 'success'
  if (label.startsWith('BACKEND VERIFIED')) return 'warning'
  if (label.startsWith('DEMO')) return 'info'
  return 'warning'
}

const DocumentationPage = () => {
  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Documentation"
          description="Architecture, detection pipeline, intelligence layers and API reference"
        />
      </ScrollReveal>

      {/* Status legend */}
      <ScrollReveal direction="up" distance={20} duration={0.6} delay={0.1}>
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-3">
              {Object.entries(integrationStatusLegend).map(([label, note]) => (
                <div
                  key={label}
                  className="flex items-center gap-2 p-2 pr-3 rounded-lg bg-gray-50 text-xs"
                >
                  <Badge variant={statusVariant(label)} size="sm">{label}</Badge>
                  <span className="text-gray-500 max-w-[260px]">{note}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        {/* Table of contents */}
        <ScrollReveal direction="right" distance={16} duration={0.5}>
          <nav className="lg:sticky lg:top-24 space-y-1 self-start">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3 px-3 hidden lg:block">
              Sections
            </p>
            <div className="flex lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0 scrollbar-thin">
              {docSections.map((section) => {
                const Icon = section.icon
                return (
                  <button
                    key={section.id}
                    onClick={() => scrollToSection(section.id)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-primary-50 hover:text-primary-700 transition-colors whitespace-nowrap lg:whitespace-normal"
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    {section.title}
                  </button>
                )
              })}
            </div>
          </nav>
        </ScrollReveal>

        {/* Sections */}
        <div className="space-y-6 min-w-0">
          {docSections.map((section, index) => {
            const Icon = section.icon
            return (
              <ScrollReveal key={section.id} direction="up" distance={20} duration={0.5} delay={index * 0.03}>
                <Card
                  id={section.id}
                  className="scroll-mt-24 hover:shadow-lg transition-shadow duration-300"
                >
                  <CardContent className="pt-6 space-y-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div className="p-3 rounded-lg bg-primary-50 text-primary-600">
                          <Icon className="h-6 w-6" />
                        </div>
                        <h2 className="text-xl font-bold tracking-tight">{section.title}</h2>
                      </div>
                      <Badge variant={statusVariant(section.status.label)}>
                        {section.status.label}
                      </Badge>
                    </div>

                    <p className="text-sm font-medium text-primary-700">{section.summary}</p>

                    <div className="prose-sm text-gray-600 max-w-none space-y-3">
                      {section.body.split('\n\n').map((paragraph, i) => (
                        <p key={i}>{paragraph}</p>
                      ))}
                    </div>

                    {section.bullets && (
                      <ul className="space-y-2">
                        {section.bullets.map((bullet) => (
                          <li key={bullet} className="flex items-start gap-2 text-sm text-gray-600">
                            <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                            <span>{bullet}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {section.code && (
                      <pre className="text-xs bg-gray-50 border rounded-lg p-4 overflow-x-auto font-mono scrollbar-thin">
                        {section.code}
                      </pre>
                    )}
                  </CardContent>
                </Card>
              </ScrollReveal>
            )
          })}

          {/* API docs CTA */}
          <ScrollReveal direction="up" distance={20} duration={0.5}>
            <Card className="bg-gradient-to-r from-gray-50 to-white border-gray-200">
              <CardContent className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-lg bg-gray-100 text-gray-600">
                    <BookOpen className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">API Contract</h3>
                    <p className="text-sm text-gray-600">
                      The stable contract is documented in API_CONTRACT.md and the backend /docs UI.
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="gap-2"
                  onClick={() => window.open('http://localhost:8001/docs', '_blank')}
                >
                  Open /docs <ChevronRight className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          </ScrollReveal>
        </div>
      </div>
    </div>
  )
}

export default DocumentationPage