'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { IaCKubernetesFinOps } from '../../components/IaCKubernetesFinOps';

export default function IaCPage() {
  return (
    <Shell>
      <Page
        title="Shift-Left IaC & Container FinOps"
        subtitle="Pre-deployment Terraform plan cost & carbon diff analyzer, CI/CD budget guardrails, and Kubernetes idle waste allocation."
      >
        <IaCKubernetesFinOps />
      </Page>
    </Shell>
  );
}
