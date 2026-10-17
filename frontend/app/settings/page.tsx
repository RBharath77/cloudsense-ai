'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { SecurityIdentitySettings } from '../../components/SecurityIdentitySettings';

export default function SettingsPage() {
  return (
    <Shell>
      <Page
        title="Settings & Access Governance"
        subtitle="Manage workspace profiles, role-based access control, team members, and security audit logs."
      >
        <SecurityIdentitySettings />
      </Page>
    </Shell>
  );
}