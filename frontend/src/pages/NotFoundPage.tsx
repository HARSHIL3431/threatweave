import { motion } from 'framer-motion'
import { AlertTriangle, Home, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Link } from 'react-router-dom'

const NotFoundPage = () => {
  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full"
      >
        <Card>
          <CardHeader className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-100 text-yellow-600 mb-4 mx-auto">
              <AlertTriangle className="h-8 w-8" />
            </div>
            <CardTitle className="text-2xl">Page Not Found</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center text-gray-600">
              <p className="mb-2">
                The page you're looking for doesn't exist or has been moved.
              </p>
              <p>
                You might have mistyped the address or the page may have moved to a different location.
              </p>
            </div>

            <div className="space-y-3">
              <h4 className="font-medium">Suggested Pages</h4>
              <ul className="space-y-2">
                <li>
                  <Link
                    to="/"
                    className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    <Home className="h-4 w-4" />
                    <div>
                      <p className="font-medium">Landing Page</p>
                      <p className="text-sm text-gray-500">Overview of the anomaly detection platform</p>
                    </div>
                  </Link>
                </li>
                <li>
                  <Link
                    to="/dashboard"
                    className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    <Home className="h-4 w-4" />
                    <div>
                      <p className="font-medium">Dashboard</p>
                      <p className="text-sm text-gray-500">System monitoring and analytics</p>
                    </div>
                  </Link>
                </li>
                <li>
                  <Link
                    to="/detect"
                    className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    <Home className="h-4 w-4" />
                    <div>
                      <p className="font-medium">Detection</p>
                      <p className="text-sm text-gray-500">Submit network flows for analysis</p>
                    </div>
                  </Link>
                </li>
              </ul>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <Link to="/" className="flex-1">
                <Button className="w-full gap-2">
                  <Home className="h-4 w-4" />
                  Go to Home
                </Button>
              </Link>
              <Button
                variant="outline"
                className="gap-2"
                onClick={() => window.history.back()}
              >
                <ArrowLeft className="h-4 w-4" />
                Go Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

export default NotFoundPage