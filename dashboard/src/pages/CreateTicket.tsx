import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreateTicket } from '../hooks/useTickets'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Loader2, ArrowRight, DollarSign, Key, Package } from 'lucide-react'

interface ExampleTicket {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  data: {
    customer_id: string
    subject: string
    body: string
  }
}

const exampleTickets: ExampleTicket[] = [
  {
    icon: DollarSign,
    title: 'Refund Request',
    description: 'Triggers the approval workflow',
    data: {
      customer_id: 'demo@customer.com',
      subject: 'Refund request for damaged item',
      body: 'I ordered a laptop (order #ORD-12345) but it arrived with a cracked screen. Please process a full refund of $999.99.',
    },
  },
  {
    icon: Key,
    title: 'Password Reset',
    description: 'Quick auto-resolution',
    data: {
      customer_id: 'user@example.com',
      subject: 'Password reset needed',
      body: 'I forgot my password and cannot log into my account. My username is john_doe123. Please help me reset it.',
    },
  },
  {
    icon: Package,
    title: 'Order Status',
    description: 'Uses the order lookup tool',
    data: {
      customer_id: 'customer@test.com',
      subject: 'Where is my order?',
      body: "I placed order #ORD-98765 three days ago and haven't received any shipping updates. Can you tell me where my package is?",
    },
  },
]

export function CreateTicket() {
  const navigate = useNavigate()
  const createTicket = useCreateTicket()

  const [formData, setFormData] = useState({
    customer_id: '',
    subject: '',
    body: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const result = await createTicket.mutateAsync(formData)
      toast.success('Ticket created successfully', {
        description: `Ticket ${result.ticket_id.slice(0, 8)}... is now being processed`,
      })
      navigate(`/tickets/${result.ticket_id}`)
    } catch (error) {
      toast.error('Failed to create ticket', {
        description: error instanceof Error ? error.message : 'Please try again',
      })
    }
  }

  const isFormValid = formData.customer_id && formData.subject && formData.body

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create New Ticket</h1>
        <p className="text-muted-foreground">
          Submit a support ticket and watch it get processed by the AI agent in real-time.
        </p>
      </div>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle>Ticket Details</CardTitle>
          <CardDescription>Fill in the information below to create a new support ticket.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Customer Email */}
            <div className="space-y-2">
              <Label htmlFor="customer_id">Customer Email</Label>
              <Input
                type="email"
                id="customer_id"
                required
                maxLength={100}
                value={formData.customer_id}
                onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
                placeholder="customer@example.com"
              />
            </div>

            {/* Subject */}
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                type="text"
                id="subject"
                required
                maxLength={500}
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="Brief description of your issue"
              />
            </div>

            {/* Message Body */}
            <div className="space-y-2">
              <Label htmlFor="body">Message</Label>
              <Textarea
                id="body"
                required
                rows={6}
                maxLength={10000}
                value={formData.body}
                onChange={(e) => setFormData({ ...formData, body: e.target.value })}
                placeholder="Describe your issue in detail..."
                className="resize-none"
              />
              <p className="text-xs text-muted-foreground">
                {formData.body.length.toLocaleString()} / 10,000 characters
              </p>
            </div>

            {/* Error Message */}
            {createTicket.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {createTicket.error instanceof Error ? createTicket.error.message : 'Failed to create ticket'}
                </AlertDescription>
              </Alert>
            )}

            {/* Submit Button */}
            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setFormData({ customer_id: '', subject: '', body: '' })}
                disabled={createTicket.isPending}
              >
                Clear
              </Button>
              <Button
                type="submit"
                disabled={createTicket.isPending || !isFormValid}
              >
                {createTicket.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    Create Ticket
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Example Tickets */}
      <Card>
        <CardHeader>
          <CardTitle>Try an Example</CardTitle>
          <CardDescription>Click any example below to pre-fill the form with a test scenario.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3">
            {exampleTickets.map((example) => {
              const Icon = example.icon
              return (
                <button
                  key={example.title}
                  type="button"
                  onClick={() => setFormData(example.data)}
                  className="flex items-center gap-4 p-4 rounded-lg border bg-card text-left transition-colors hover:bg-muted/50 hover:border-primary/50"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{example.title}</p>
                    <p className="text-sm text-muted-foreground">{example.description}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
