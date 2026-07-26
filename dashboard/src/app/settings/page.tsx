'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Settings,
  Key,
  Bell,
  Shield,
  Database,
  RefreshCw,
  Check,
  AlertTriangle,
} from 'lucide-react';
import { useAllServicesHealth, useEvidence } from '@/lib/hooks';
import {
  api,
  API_CONFIG,
  DASHBOARD_SESSION_KEYS,
} from '@/lib/api';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge, StatusBadge } from '@/components/ui/badge';
import { StatusIndicator, PulsingIndicator } from '@/components/ui/status-indicator';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tabs, TabPanel } from '@/components/ui/tabs';

// =============================================================================
// SETTINGS PAGE
// =============================================================================

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('api');

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure your STIX dashboard and integrations
        </p>
      </div>

      <Tabs
        tabs={[
          { id: 'api', label: 'API Configuration', icon: <Key className="h-4 w-4" /> },
          { id: 'services', label: 'Services', icon: <Database className="h-4 w-4" /> },
          { id: 'notifications', label: 'Notifications', icon: <Bell className="h-4 w-4" /> },
          { id: 'security', label: 'Security', icon: <Shield className="h-4 w-4" /> },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      <TabPanel active={activeTab === 'api'}>
        <ApiSettings />
      </TabPanel>

      <TabPanel active={activeTab === 'services'}>
        <ServicesSettings />
      </TabPanel>

      <TabPanel active={activeTab === 'notifications'}>
        <NotificationSettings />
      </TabPanel>

      <TabPanel active={activeTab === 'security'}>
        <SecuritySettings />
      </TabPanel>
    </div>
  );
}

// =============================================================================
// API SETTINGS
// =============================================================================

function ApiSettings() {
  const [apiKey, setApiKey] = useState('');
  const [operatorId, setOperatorId] = useState('dashboard-user');
  const [operatorRole, setOperatorRole] = useState('security_admin');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.restoreSession();
    const stored = localStorage.getItem(DASHBOARD_SESSION_KEYS.apiKey);
    if (stored) setApiKey(stored);
    const operator = api.getOperatorIdentity();
    setOperatorId(operator.id);
    setOperatorRole(operator.role);
  }, []);

  const handleSave = () => {
    const operator = {
      id: operatorId.trim() || 'dashboard-user',
      role: operatorRole.trim() || 'security_admin',
    };
    localStorage.setItem(DASHBOARD_SESSION_KEYS.apiKey, apiKey.trim());
    localStorage.setItem(DASHBOARD_SESSION_KEYS.operator, JSON.stringify(operator));
    api.setApiKey(apiKey);
    api.setOperatorIdentity(operator);
    window.dispatchEvent(new Event('stix-session-updated'));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="API Key"
          description="Configure your API key for authenticating with STIX services"
        />
        <CardContent>
          <div className="space-y-4 max-w-md">
            <Input
              label="API Key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your STIX API key"
            />
            <p className="text-xs text-gray-500">
              The API key is stored locally in your browser and used to authenticate
              requests to the STIX services.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Approver ID"
                value={operatorId}
                onChange={(e) => setOperatorId(e.target.value)}
                placeholder="security-operator"
              />
              <Input
                label="Approver Role"
                value={operatorRole}
                onChange={(e) => setOperatorRole(e.target.value)}
                placeholder="security_admin"
              />
            </div>
            <p className="text-xs text-gray-500">
              Approval actions submit this identity and must match the ticket&apos;s required role.
            </p>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={handleSave}>
            {saved ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Saved
              </>
            ) : (
              'Save API Key'
            )}
          </Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader
          title="Service Endpoints"
          description="Configure the URLs for STIX services"
        />
        <CardContent>
          <div className="grid gap-4 max-w-lg">
            <Input
              label="Enforcer URL"
              value={API_CONFIG.enforcer}
              disabled
              helperText="Set via NEXT_PUBLIC_ENFORCER_URL environment variable"
            />
            <Input
              label="Policy URL"
              value={API_CONFIG.policy}
              disabled
              helperText="Set via NEXT_PUBLIC_POLICY_URL environment variable"
            />
            <Input
              label="Evidence URL"
              value={API_CONFIG.evidence}
              disabled
              helperText="Set via NEXT_PUBLIC_EVIDENCE_URL environment variable"
            />
            <Input
              label="Approvals URL"
              value={API_CONFIG.approvals}
              disabled
              helperText="Set via NEXT_PUBLIC_APPROVALS_URL environment variable"
            />
            <Input
              label="Fabric URL"
              value={API_CONFIG.fabric}
              disabled
              helperText="Set via NEXT_PUBLIC_FABRIC_URL environment variable"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// SERVICES SETTINGS
// =============================================================================

function ServicesSettings() {
  const { data: health, isLoading, refetch } = useAllServicesHealth();

  const services = [
    { key: 'enforcer', name: 'Enforcer', description: 'Authorization decision engine' },
    { key: 'policy', name: 'Policy', description: 'Policy management and evaluation' },
    { key: 'evidence', name: 'Evidence', description: 'Immutable audit trail storage' },
    { key: 'approvals', name: 'Approvals', description: 'Human-in-the-loop workflow' },
    { key: 'fabric', name: 'Fabric', description: 'Agent policy fabric registry and graph' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Service Health</h3>
          <p className="text-sm text-gray-500">Monitor the health of STIX services</p>
        </div>
        <Button variant="secondary" onClick={() => refetch()}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-4">
        {services.map((service) => {
          const serviceHealth = health?.[service.key as keyof typeof health];
          const status = serviceHealth?.status || 'unknown';

          return (
            <Card key={service.key}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <PulsingIndicator
                    status={status === 'unknown' ? 'unhealthy' : status}
                  />
                  <div>
                    <p className="font-medium">{service.name}</p>
                    <p className="text-sm text-gray-500">{service.description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <StatusBadge status={status} />
                  {serviceHealth && (
                    <p className="text-xs text-gray-500 mt-1">
                      v{serviceHealth.version} | Uptime:{' '}
                      {Math.floor(serviceHealth.uptime_ms / 1000 / 60 / 60)}h
                    </p>
                  )}
                </div>
              </div>

              {serviceHealth?.checks && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-xs font-medium text-gray-500 mb-2">Health Checks</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {Object.entries(serviceHealth.checks).map(([check, result]) => (
                      <div
                        key={check}
                        className="flex items-center gap-2 text-xs p-2 bg-gray-50 rounded"
                      >
                        <StatusIndicator
                          status={result.status === 'ok' ? 'healthy' : 'unhealthy'}
                          size="sm"
                        />
                        <span>{check}</span>
                        <span className="text-gray-400">{result.latency_ms}ms</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// NOTIFICATION SETTINGS
// =============================================================================

function NotificationSettings() {
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [webhookEnabled, setWebhookEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [pendingThreshold, setPendingThreshold] = useState('immediate');
  const [denialThreshold, setDenialThreshold] = useState('10');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const raw = localStorage.getItem('stix_notification_settings');
    if (!raw) return;
    try {
      const settings = JSON.parse(raw) as Partial<Record<string, string | boolean>>;
      if (typeof settings.emailEnabled === 'boolean') setEmailEnabled(settings.emailEnabled);
      if (typeof settings.slackEnabled === 'boolean') setSlackEnabled(settings.slackEnabled);
      if (typeof settings.webhookEnabled === 'boolean') setWebhookEnabled(settings.webhookEnabled);
      if (typeof settings.webhookUrl === 'string') setWebhookUrl(settings.webhookUrl);
      if (typeof settings.pendingThreshold === 'string') setPendingThreshold(settings.pendingThreshold);
      if (typeof settings.denialThreshold === 'string') setDenialThreshold(settings.denialThreshold);
    } catch {
      localStorage.removeItem('stix_notification_settings');
    }
  }, []);

  const saveSettings = () => {
    localStorage.setItem('stix_notification_settings', JSON.stringify({
      emailEnabled,
      slackEnabled,
      webhookEnabled,
      webhookUrl,
      pendingThreshold,
      denialThreshold,
    }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Notification Channels"
          description="Configure how you receive alerts for pending approvals and policy violations"
        />
        <CardContent>
          <div className="space-y-4">
            <label className="flex items-center justify-between p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
              <div>
                <p className="font-medium">Email Notifications</p>
                <p className="text-sm text-gray-500">
                  Receive email alerts for pending approvals
                </p>
              </div>
              <input
                type="checkbox"
                checked={emailEnabled}
                onChange={(e) => setEmailEnabled(e.target.checked)}
                className="h-5 w-5 text-blue-600"
              />
            </label>

            <label className="flex items-center justify-between p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
              <div>
                <p className="font-medium">Slack Integration</p>
                <p className="text-sm text-gray-500">
                  Post alerts to a Slack channel
                </p>
              </div>
              <input
                type="checkbox"
                checked={slackEnabled}
                onChange={(e) => setSlackEnabled(e.target.checked)}
                className="h-5 w-5 text-blue-600"
              />
            </label>

            <label className="flex items-center justify-between p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
              <div>
                <p className="font-medium">Webhook</p>
                <p className="text-sm text-gray-500">
                  Send alerts to a custom webhook endpoint
                </p>
              </div>
              <input
                type="checkbox"
                checked={webhookEnabled}
                onChange={(e) => setWebhookEnabled(e.target.checked)}
                className="h-5 w-5 text-blue-600"
              />
            </label>

            {webhookEnabled && (
              <div className="pl-4 border-l-2 border-blue-200">
                <Input
                  label="Webhook URL"
                  placeholder="https://example.com/webhook"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={saveSettings}>{saved ? 'Saved' : 'Save Notification Settings'}</Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader
          title="Alert Thresholds"
          description="Configure when to trigger alerts"
        />
        <CardContent>
          <div className="space-y-4 max-w-md">
            <Select
              label="Pending Approval Alert"
              value={pendingThreshold}
              onChange={(e) => setPendingThreshold(e.target.value)}
              options={[
                { value: 'immediate', label: 'Immediately' },
                { value: '5min', label: 'After 5 minutes' },
                { value: '15min', label: 'After 15 minutes' },
                { value: '1hour', label: 'After 1 hour' },
              ]}
            />
            <Select
              label="Denial Rate Alert"
              value={denialThreshold}
              onChange={(e) => setDenialThreshold(e.target.value)}
              options={[
                { value: '5', label: '>5% denial rate' },
                { value: '10', label: '>10% denial rate' },
                { value: '25', label: '>25% denial rate' },
                { value: 'off', label: 'Disabled' },
              ]}
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={saveSettings}>{saved ? 'Saved' : 'Save Notification Settings'}</Button>
        </CardFooter>
      </Card>
    </div>
  );
}

// =============================================================================
// SECURITY SETTINGS
// =============================================================================

function SecuritySettings() {
  const [sessionTimeout, setSessionTimeout] = useState('30');
  const [requireReauth, setRequireReauth] = useState(true);
  const [saved, setSaved] = useState(false);
  const { data: recentEvidence, isLoading: evidenceLoading } = useEvidence({ page: 1, page_size: 5 });

  useEffect(() => {
    const raw = localStorage.getItem('stix_security_settings');
    if (!raw) return;
    try {
      const settings = JSON.parse(raw) as Partial<{ sessionTimeout: string; requireReauth: boolean }>;
      if (settings.sessionTimeout) setSessionTimeout(settings.sessionTimeout);
      if (typeof settings.requireReauth === 'boolean') setRequireReauth(settings.requireReauth);
    } catch {
      localStorage.removeItem('stix_security_settings');
    }
  }, []);

  const saveSecuritySettings = () => {
    localStorage.setItem('stix_security_settings', JSON.stringify({ sessionTimeout, requireReauth }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const clearLocalData = () => {
    localStorage.removeItem(DASHBOARD_SESSION_KEYS.apiKey);
    localStorage.removeItem(DASHBOARD_SESSION_KEYS.operator);
    localStorage.removeItem('stix_notification_settings');
    localStorage.removeItem('stix_security_settings');
    window.dispatchEvent(new Event('stix-session-updated'));
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Session Security"
          description="Configure security settings for your dashboard session"
        />
        <CardContent>
          <div className="space-y-4 max-w-md">
            <Select
              label="Session Timeout"
              value={sessionTimeout}
              onChange={(e) => setSessionTimeout(e.target.value)}
              options={[
                { value: '15', label: '15 minutes' },
                { value: '30', label: '30 minutes' },
                { value: '60', label: '1 hour' },
                { value: '240', label: '4 hours' },
              ]}
            />
            <label className="flex items-center gap-3">
              <input type="checkbox" className="h-4 w-4 text-blue-600" checked={requireReauth} onChange={(e) => setRequireReauth(e.target.checked)} />
              <span className="text-sm">Require re-authentication for approval actions</span>
            </label>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={saveSecuritySettings}>{saved ? 'Saved' : 'Save Security Settings'}</Button>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader
          title="Audit Log"
          description="View recent actions taken in this dashboard"
        />
        <CardContent>
          <div className="space-y-3">
            {evidenceLoading ? <LoadingSpinner size="sm" /> : (recentEvidence?.data ?? []).map((record) => (
              <div
                key={record.event_id}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div>
                  <p className="text-sm font-medium">{record.decision} {record.action}</p>
                  <p className="text-xs text-gray-500">{record.actor_id} · {record.trace_id}</p>
                </div>
                <span className="text-xs text-gray-400">{new Date(record.timestamp).toLocaleString()}</span>
              </div>
            ))}
            {!evidenceLoading && !recentEvidence?.data.length && <p className="text-sm text-gray-500">No recent evidence records.</p>}
          </div>
        </CardContent>
        <CardFooter>
          <Link href="/evidence"><Button variant="secondary">View Full Audit Log</Button></Link>
        </CardFooter>
      </Card>

      <Card className="border-red-200 bg-red-50">
        <CardHeader
          title="Danger Zone"
          description="Irreversible actions"
        />
        <CardContent>
          <div className="flex items-center justify-between p-4 bg-white rounded-lg border border-red-200">
            <div>
              <p className="font-medium text-red-700">Clear Local Data</p>
              <p className="text-sm text-gray-500">
                Remove all locally stored settings and cached data
              </p>
            </div>
            <Button variant="danger" size="sm" onClick={clearLocalData}>
              Clear Data
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
