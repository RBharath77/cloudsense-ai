'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { SystemObservabilityActions } from '../../components/SystemObservabilityActions';

export default function SystemPage() {
  return (
    <Shell>
      <Page
        title="System Observability & Automated Action Engine"
        subtitle="Real-time telemetry, asynchronous jobs, HMAC-signed webhooks, and human-in-the-loop FinOps remediation."
      >
        <SystemObservabilityActions />
      </Page>
    </Shell>
  );
}
