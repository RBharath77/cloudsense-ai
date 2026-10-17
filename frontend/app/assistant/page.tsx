'use client';

import Shell from '../../components/Shell';
import { Page } from '../../components/Page';
import { AIAnalyst } from '../../components/AIAnalyst';

export default function AssistantPage() {
  return (
    <Shell>
      <Page
        title="Grounded AI Analyst"
        subtitle="Deterministic FinOps & GreenOps Q&A engine with zero hallucinations and allowlisted tool execution."
      >
        <AIAnalyst />
      </Page>
    </Shell>
  );
}