from abc import ABC, abstractmethod
from datetime import datetime
import random

class CloudProvider(ABC):
    @abstractmethod
    def get_costs(self): ...
    @abstractmethod
    def get_resources(self): ...
    @abstractmethod
    def get_metrics(self): ...
    def get_events(self): return []
    def get_security_findings(self): return []
    def get_billing_data(self): return self.get_costs()

class MockCloudProvider(CloudProvider):
    def __init__(self, provider, seed=42):
        self.provider=provider; self.r=random.Random(seed+hash(provider)%1000)
    def get_costs(self): return {"provider":self.provider,"amount":round(self.r.uniform(100,500),2),"timestamp":datetime.utcnow().isoformat()}
    def get_resources(self):
        return [{"name":f"{self.provider.lower()}-resource-{i}","type":"compute","region":"us-east-1","utilization":round(self.r.uniform(15,95),1)} for i in range(10)]
    def get_metrics(self): return []

class AWSProvider(MockCloudProvider):
    def __init__(self): super().__init__("AWS")
class AzureProvider(MockCloudProvider):
    def __init__(self): super().__init__("Azure")
class GCPProvider(MockCloudProvider):
    def __init__(self): super().__init__("GCP")
