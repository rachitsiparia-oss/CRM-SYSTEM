"use client";

import { useCommunicationChannels, useUpdateCommunicationChannel } from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Switch } from "@/components/ui/switch";

function ChannelRow({ channelId, canManage }: { channelId: string; canManage: boolean }) {
  const { data: channels } = useCommunicationChannels();
  const channel = channels?.find((c) => c.id === channelId);
  const updateChannel = useUpdateCommunicationChannel(channelId);
  if (!channel) return null;

  return (
    <SectionCard
      title={channel.name}
      description={channel.provider ? `Provider: ${channel.provider}` : "No provider configured"}
      actions={
        <StatusBadge
          label={channel.is_enabled ? "Enabled" : "Disabled"}
          tone={channel.is_enabled ? "success" : "neutral"}
        />
      }
    >
      <div className="flex flex-wrap gap-6">
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={channel.is_enabled}
            disabled={!canManage}
            onCheckedChange={(checked) => void updateChannel.mutateAsync({ is_enabled: checked })}
          />
          Enabled
        </label>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={channel.inbound_enabled}
            disabled={!canManage}
            onCheckedChange={(checked) => void updateChannel.mutateAsync({ inbound_enabled: checked })}
          />
          Inbound
        </label>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={channel.outbound_enabled}
            disabled={!canManage}
            onCheckedChange={(checked) => void updateChannel.mutateAsync({ outbound_enabled: checked })}
          />
          Outbound
        </label>
      </div>
      <p className="text-muted-foreground mt-3 text-xs">
        {channel.requires_template ? "Requires an approved template for outbound sends." : "No template required."}
        {channel.business_hours_restricted ? " Restricted to business hours." : ""}
      </p>
    </SectionCard>
  );
}

export function ChannelsView() {
  const { data: currentUser } = useCurrentUser();
  const { data: channels, isLoading } = useCommunicationChannels();
  const canManage = hasPermission(currentUser, "communications.channels.manage");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Channels & providers"
        description="Every channel currently defaults to the internal mock provider. Live WhatsApp, SMS, and email credentials are wired in a later phase."
      />

      {isLoading ? (
        <CardSkeleton />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {(channels ?? []).map((channel) => (
            <ChannelRow key={channel.id} channelId={channel.id} canManage={canManage} />
          ))}
        </div>
      )}
    </div>
  );
}
