import { motion } from 'framer-motion'
import { ArrowRight, Shield, Zap, Brain, BarChart, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import SystemPipelineDemo from '@/features/landing/SystemPipelineDemo'
import { Link } from 'react-router-dom'
import ScrollReveal from '@/components/animations/ScrollReveal'
import SectionTransition, { SectionItem } from '@/components/animations/SectionTransition'

const LandingPage = () => {
  const features = [
    {
      icon: <Shield className="h-8 w-8" />,
      title: 'ML-Powered Detection',
      description: 'Isolation Forest anomaly detection trained on CICIDS2017 dataset with frozen E2 experiment artifacts.'
    },
    {
      icon: <Zap className="h-8 w-8" />,
      title: 'Real-time Analysis',
      description: 'Submit network flows and receive anomaly scores with severity classification in milliseconds.'
    },
    {
      icon: <Brain className="h-8 w-8" />,
      title: 'Intelligence Layers',
      description: 'Modular architecture for MITRE ATT&CK context, RAG knowledge retrieval, and LLM explanations.'
    },
    {
      icon: <BarChart className="h-8 w-8" />,
      title: 'Comprehensive Dashboard',
      description: 'Monitor detection activity, system health, and performance metrics in a security-focused interface.'
    },
    {
      icon: <AlertTriangle className="h-8 w-8" />,
      title: 'Severity Classification',
      description: 'Risk-based severity scoring with clear thresholds for actionable security insights.'
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 md:py-32">
        <div className="container mx-auto px-4">
          <ScrollReveal direction="up" distance={30} duration={0.8}>
            <div className="max-w-4xl mx-auto text-center">
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 text-primary-700 text-sm font-medium mb-6"
              >
                <Shield className="h-4 w-4" />
                AI-Powered Cybersecurity Platform
              </motion.div>
              
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.3 }}
                className="text-4xl md:text-6xl font-bold tracking-tight mb-6"
              >
                Detect Network Anomalies with{' '}
                <span className="bg-gradient-to-r from-primary-600 to-blue-600 bg-clip-text text-transparent">
                  Machine Learning
                </span>
              </motion.h1>
              
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.4 }}
                className="text-xl text-gray-600 mb-10 max-w-3xl mx-auto"
              >
                An interactive platform for detecting anomalous network flows using Isolation Forest models.
                Experience the complete ML pipeline from raw network data to actionable security insights.
              </motion.p>
              
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.5 }}
                className="flex flex-col sm:flex-row gap-4 justify-center"
              >
                <Link to="/detect">
                  <Button size="lg" className="gap-2 hover:scale-105 transition-transform">
                    Try Detection Now
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link to="/dashboard">
                  <Button size="lg" variant="outline" className="hover:scale-105 transition-transform">
                    View Dashboard
                  </Button>
                </Link>
              </motion.div>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* Interactive System Demo */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <SectionTransition delay={0.2} staggerChildren={0.15}>
            <div className="max-w-6xl mx-auto">
              <SectionItem>
                <div className="text-center mb-12">
                  <h2 className="text-3xl font-bold mb-4">How It Works</h2>
                  <p className="text-gray-600 max-w-2xl mx-auto">
                    Watch the complete journey of a network flow through our detection system.
                    Each stage transforms the data, culminating in actionable security intelligence.
                  </p>
                </div>
              </SectionItem>
              
              <SectionItem>
                <SystemPipelineDemo />
              </SectionItem>
            </div>
          </SectionTransition>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <SectionTransition delay={0.1}>
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-4">Platform Features</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                A modular, enterprise-ready platform built for cybersecurity professionals and researchers.
              </p>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, index) => (
                <SectionItem key={index}>
                  <Card className="h-full hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
                    <CardHeader>
                      <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-primary-100 text-primary-600 mb-4">
                        {feature.icon}
                      </div>
                      <CardTitle>{feature.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <CardDescription>{feature.description}</CardDescription>
                    </CardContent>
                  </Card>
                </SectionItem>
              ))}
            </div>
          </SectionTransition>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <ScrollReveal direction="up" distance={20} duration={0.6}>
            <div className="max-w-4xl mx-auto text-center">
              <Card className="bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200 hover:shadow-xl transition-shadow duration-300">
                <CardHeader>
                  <CardTitle className="text-2xl md:text-3xl">
                    Ready to Analyze Your Network Flows?
                  </CardTitle>
                  <CardDescription className="text-lg">
                    Experience real anomaly detection with our frozen E2 Isolation Forest model.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <Link to="/detect">
                      <Button size="lg" className="gap-2 hover:scale-105 transition-transform">
                        Start Detection
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                    <a 
                      href="https://github.com/your-repo" 
                      target="_blank" 
                      rel="noopener noreferrer"
                    >
                      <Button size="lg" variant="outline" className="hover:scale-105 transition-transform">
                        View Documentation
                      </Button>
                    </a>
                  </div>
                </CardContent>
              </Card>
            </div>
          </ScrollReveal>
        </div>
      </section>
    </div>
  )
}

export default LandingPage