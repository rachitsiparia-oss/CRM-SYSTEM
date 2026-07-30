"use client";

import { useState } from "react";
import { Search } from "lucide-react";

import { useCustomerList } from "@/lib/hooks/use-customers";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/empty-state";
import { CustomerPreferenceForm } from "./customer-preference-form";

export function PreferencesView() {
  const [searchInput, setSearchInput] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const search = useDebouncedValue(searchInput);

  const { data } = useCustomerList({
    page: 1,
    pageSize: 10,
    search: search || undefined,
  });

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Communication preferences"
        description="Per-customer channel preferences, quiet hours, and transactional/promotional consent."
      />

      <SectionCard title="Find a customer">
        <div className="relative">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            className="pl-8"
            placeholder="Search by name, phone, or email…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>
        {search && (data?.data.length ?? 0) > 0 && (
          <ul className="mt-3 flex flex-col gap-1">
            {data?.data.map((customer) => (
              <li key={customer.id}>
                <button
                  className="hover:bg-accent w-full rounded-md p-2 text-left text-sm"
                  onClick={() => setSelectedCustomerId(customer.id)}
                >
                  {customer.display_name} — {customer.primary_phone_e164 ?? customer.primary_email}
                </button>
              </li>
            ))}
          </ul>
        )}
        {search && data?.data.length === 0 && (
          <p className="text-muted-foreground mt-3 text-sm">No customers match this search.</p>
        )}
      </SectionCard>

      {selectedCustomerId ? (
        <CustomerPreferenceForm customerId={selectedCustomerId} />
      ) : (
        <EmptyState
          icon={Search}
          title="Search for a customer"
          description="Select a customer above to view or edit their communication preferences."
        />
      )}
    </div>
  );
}
