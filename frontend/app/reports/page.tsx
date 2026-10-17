'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { ReportsManager } from '../../components/ReportsManager';

export default function ReportsPage() {
  return (
    <Shell>
      <Page
        title="Executive Reports & Digests"
        subtitle="Database-reconciled FinOps intelligence digests in PDF & sanitized CSV formats."
      >
        <ReportsManager />
      </Page>
    </Shell>
  );
}
