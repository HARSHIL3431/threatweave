import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Compass, HelpCircle, LifeBuoy, MessageSquareText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import PageHeader from '@/components/ui/PageHeader'
import ScrollReveal from '@/components/animations/ScrollReveal'
import { gettingStartedSteps, faqs, supportPlaceholder } from '@/data/mock/help'
import { cn } from '@/utils/cn'

const HelpPage = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0)

  return (
    <div className="space-y-8">
      {/* Header */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <PageHeader
          title="Help & Support"
          description="Getting started, FAQ and how the platform communicates results"
        />
      </ScrollReveal>

      {/* Getting Started */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <Compass className="h-5 w-5 text-primary-600" />
            <CardTitle>Getting Started</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
              {gettingStartedSteps.map((step, index) => {
                const Icon = step.icon
                return (
                  <div
                    key={step.id}
                    className="p-5 rounded-xl border border-gray-200 hover:border-primary-200 hover:bg-primary-50/30 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-9 h-9 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center flex-shrink-0">
                        <Icon className="h-5 w-5" />
                      </div>
                      <h3 className="font-semibold">
                        <span className="text-gray-400 text-sm font-bold mr-1">{index + 1}.</span>
                        {step.title}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600">{step.body}</p>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>

      {/* FAQ */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <HelpCircle className="h-5 w-5 text-primary-600" />
            <CardTitle>Frequently Asked Questions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {faqs.map((faq, index) => {
              const isOpen = openFaq === index
              return (
                <div
                  key={faq.question}
                  className={cn(
                    'rounded-xl border transition-colors',
                    isOpen ? 'border-primary-200 bg-primary-50/30' : 'border-gray-200 hover:border-gray-300'
                  )}
                >
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : index)}
                    className="w-full flex items-center justify-between gap-3 p-4 text-left"
                  >
                    <span className="font-medium text-sm">{faq.question}</span>
                    <ChevronDown
                      className={cn(
                        'h-5 w-5 text-gray-500 flex-shrink-0 transition-transform duration-200',
                        isOpen && 'rotate-180'
                      )}
                    />
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4 text-sm text-gray-600 leading-relaxed">
                          {faq.answer}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </CardContent>
        </Card>
      </ScrollReveal>

      {/* Support */}
      <ScrollReveal direction="up" distance={20} duration={0.6}>
        <Card className="bg-gradient-to-r from-gray-50 to-white border-gray-200">
          <CardContent className="pt-6 flex flex-col sm:flex-row items-start gap-4">
            <div className="p-3 rounded-lg bg-gray-100 text-gray-600">
              <LifeBuoy className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h3 className="font-semibold text-lg">{supportPlaceholder.title}</h3>
              <p className="text-sm text-gray-600">{supportPlaceholder.note}</p>
              <div className="flex items-center gap-2 pt-2 text-xs text-gray-500">
                <MessageSquareText className="h-4 w-4" />
                For answers, refer to the Documentation page and the API contract in the repository.
              </div>
            </div>
          </CardContent>
        </Card>
      </ScrollReveal>
    </div>
  )
}

export default HelpPage