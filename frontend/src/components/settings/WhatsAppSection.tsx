import { useCallback, useEffect, useState } from 'react';
import { listMembers } from '../../api/households';
import type { AvailableWhatsAppGroup, Member, OutgoingMessage, WhatsAppGroup, WhatsAppStatus } from '../../api/types';
import {
  addWhatsAppGroup,
  connectWhatsApp,
  disconnectWhatsApp,
  getWhatsAppStatus,
  listAvailableGroups,
  listOutgoingMessages,
  listWhatsAppGroups,
  removeWhatsAppGroup,
  sendWhatsAppTest,
  setWhatsAppGroupActive,
} from '../../api/whatsapp';
import { useMessage } from '../../contexts/MessageContext';
import { MessageKey, useI18n } from '../../i18n';
import { shortDate } from '../../utils/format';
import { ConfirmModal } from '../ConfirmModal';

const POLL_MS = 3000;

/** Managers: link a WhatsApp number to the household, pick its groups, see what was sent. */
export function WhatsAppSection({ householdId }: { householdId: string }) {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const showMessage = useMessage();

  const loadStatus = useCallback(() => {
    getWhatsAppStatus(householdId)
      .then(setStatus)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(loadStatus, [loadStatus]);

  // While linking, poll for the QR code and for the scan
  const waiting = status?.status === 'connecting' || status?.status === 'qr';
  useEffect(() => {
    if (!waiting) return;
    const timer = window.setInterval(loadStatus, POLL_MS);
    return () => window.clearInterval(timer);
  }, [waiting, loadStatus]);

  return (
    <>
      <ConnectionCard householdId={householdId} status={status} onStatus={setStatus} onRetry={loadStatus} />
      {status && status.status !== 'off' && (
        <>
          <GroupsCard householdId={householdId} connected={status.status === 'connected'} />
          <IndividualsCard householdId={householdId} connected={status.status === 'connected'} />
          <MessagesCard householdId={householdId} />
        </>
      )}
    </>
  );
}

function ConnectionCard({
  householdId,
  status,
  onStatus,
  onRetry,
}: {
  householdId: string;
  status: WhatsAppStatus | null;
  onStatus: (status: WhatsAppStatus) => void;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const [busy, setBusy] = useState(false);
  const [confirmUnlink, setConfirmUnlink] = useState(false);

  const run = async (action: () => Promise<WhatsAppStatus>) => {
    setBusy(true);
    try {
      onStatus(await action());
    } catch (e) {
      showMessage('error', (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const body = () => {
    if (!status) return <p className="muted">{t('common.loading')}</p>;
    switch (status.status) {
      case 'off':
        return <p className="muted">{t('whatsapp.off')}</p>;
      case 'unavailable':
        return (
          <>
            <p className="negative">{t('whatsapp.unavailable')}</p>
            {status.error && <p className="muted small">{status.error}</p>}
            <div className="row" style={{ marginTop: 12 }}>
              <button className="button button--secondary" onClick={onRetry}>
                {t('whatsapp.retry')}
              </button>
            </div>
          </>
        );
      case 'connecting':
        return <p className="muted">{t('whatsapp.connecting')}</p>;
      case 'qr':
        return (
          <div className="wa-qr">
            {status.qr && <img className="wa-qr__image" src={status.qr} alt={t('whatsapp.qrAlt')} width={240} height={240} />}
            <ol className="wa-qr__steps">
              <li>{t('whatsapp.step1')}</li>
              <li>{t('whatsapp.step2')}</li>
              <li>{t('whatsapp.step3')}</li>
            </ol>
          </div>
        );
      case 'connected':
        return (
          <>
            <p>
              <span className="pill pill--open">{t('whatsapp.connected')}</span>{' '}
              {[status.name, status.phone && `+${status.phone}`].filter(Boolean).join(' · ')}
            </p>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="button button--ghost" onClick={() => setConfirmUnlink(true)} disabled={busy}>
                {t('whatsapp.disconnect')}
              </button>
            </div>
          </>
        );
      default:
        return (
          <>
            <p className="muted">{t('whatsapp.notConnected')}</p>
            {status.error && <p className="muted small">{status.error}</p>}
            <p className="muted small" style={{ marginTop: 8 }}>
              {t('whatsapp.warning')}
            </p>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="button button--primary" onClick={() => run(() => connectWhatsApp(householdId))} disabled={busy}>
                {busy ? t('common.working') : t('whatsapp.connect')}
              </button>
            </div>
          </>
        );
    }
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('whatsapp.connectionTitle')}
      </h2>
      <p className="muted small" style={{ marginBottom: 10 }}>
        {t('whatsapp.connectionHint')}
      </p>
      {body()}
      {confirmUnlink && (
        <ConfirmModal
          title={t('whatsapp.disconnectConfirmTitle')}
          confirmLabel={t('whatsapp.disconnect')}
          danger
          onClose={() => setConfirmUnlink(false)}
          onConfirm={() => run(() => disconnectWhatsApp(householdId))}
        >
          {t('whatsapp.disconnectConfirmBody')}
        </ConfirmModal>
      )}
    </section>
  );
}

function GroupsCard({ householdId, connected }: { householdId: string; connected: boolean }) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const [groups, setGroups] = useState<WhatsAppGroup[] | null>(null);
  const [available, setAvailable] = useState<AvailableWhatsAppGroup[] | null>(null);
  const [picking, setPicking] = useState(false);

  const load = useCallback(() => {
    listWhatsAppGroups(householdId)
      .then(setGroups)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  const run = async (action: () => Promise<unknown>, success?: string) => {
    try {
      await action();
      if (success) showMessage('success', success);
      load();
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  const openPicker = async () => {
    setPicking(true);
    setAvailable(null);
    try {
      setAvailable(await listAvailableGroups(householdId));
      load(); // names may have been refreshed
    } catch (e) {
      showMessage('error', (e as Error).message);
      setPicking(false);
    }
  };

  const add = async (group: AvailableWhatsAppGroup) => {
    await run(() => addWhatsAppGroup(householdId, { jid: group.jid, name: group.name }), t('whatsapp.groupAdded', { name: group.name }));
    setAvailable((list) => list?.map((g) => (g.jid === group.jid ? { ...g, added: true } : g)) || null);
  };

  const remove = (group: WhatsAppGroup) => {
    if (!window.confirm(t('whatsapp.groupRemoveConfirm', { name: group.name }))) return;
    run(() => removeWhatsAppGroup(householdId, group.id), t('whatsapp.groupRemoved', { name: group.name }));
  };

  const notAdded = available?.filter((g) => !g.added) || [];

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('whatsapp.groupsTitle')}
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {t('whatsapp.groupsHint')}
      </p>
      {!groups && <p className="muted">{t('common.loading')}</p>}
      {groups?.length === 0 && <p className="muted">{t('whatsapp.groupsEmpty')}</p>}
      <div className="list">
        {groups?.map((group) => (
          <div key={group.id} className={`list-item ${group.is_active ? '' : 'list-item--disabled'}`}>
            <div className="list-item__main">
              <div className="list-item__title">{group.name}</div>
              <div className="list-item__sub">{group.is_active ? t('whatsapp.groupActive') : t('whatsapp.groupPaused')}</div>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={group.is_active}
                onChange={(e) => run(() => setWhatsAppGroupActive(householdId, group.id, e.target.checked))}
              />
              {t('whatsapp.groupSend')}
            </label>
            <button
              className="button button--ghost button--small"
              disabled={!connected}
              onClick={() => run(() => sendWhatsAppTest(householdId, { group_id: group.id }), t('whatsapp.testSent', { name: group.name }))}
            >
              {t('whatsapp.test')}
            </button>
            <button className="button button--danger button--small" onClick={() => remove(group)}>
              {t('common.remove')}
            </button>
          </div>
        ))}
      </div>

      {!picking && (
        <div className="row" style={{ marginTop: 12 }}>
          <button className="button button--secondary" onClick={openPicker} disabled={!connected}>
            + {t('whatsapp.addGroup')}
          </button>
          {!connected && <span className="muted small">{t('whatsapp.connectFirst')}</span>}
        </div>
      )}
      {picking && (
        <div className="wa-picker">
          <div className="wa-picker__header">
            <span className="form-label">{t('whatsapp.pickGroup')}</span>
            <button className="button button--ghost button--small" onClick={() => setPicking(false)}>
              {t('common.close')}
            </button>
          </div>
          {!available && <p className="muted">{t('common.loading')}</p>}
          {available && notAdded.length === 0 && <p className="muted">{t('whatsapp.noMoreGroups')}</p>}
          <div className="list">
            {notAdded.map((group) => (
              <div key={group.jid} className="list-item">
                <div className="list-item__main">
                  <div className="list-item__title">{group.name}</div>
                  <div className="list-item__sub">{t('whatsapp.participants', { count: String(group.participants) })}</div>
                </div>
                <button className="button button--primary button--small" onClick={() => add(group)}>
                  {t('common.add')}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function IndividualsCard({ householdId, connected }: { householdId: string; connected: boolean }) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const [members, setMembers] = useState<Member[] | null>(null);

  useEffect(() => {
    listMembers(householdId)
      .then((list) => setMembers(list.filter((m) => m.is_active && m.is_participant)))
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);

  const test = async (member: Member) => {
    try {
      await sendWhatsAppTest(householdId, { member_id: member.id });
      showMessage('success', t('whatsapp.testSent', { name: member.display_name }));
    } catch (e) {
      showMessage('error', (e as Error).message);
    }
  };

  return (
    <section className="card">
      <h2 className="card__title" style={{ marginBottom: 6 }}>
        {t('whatsapp.individualsTitle')}
      </h2>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {t('whatsapp.individualsHint')}
      </p>
      {!members && <p className="muted">{t('common.loading')}</p>}
      <div className="list">
        {members?.map((m) => (
          <div key={m.id} className="list-item">
            <div className="list-item__main">
              <div className="list-item__title">{m.display_name}</div>
              <div className="list-item__sub">{m.whatsapp || t('whatsapp.noNumber')}</div>
            </div>
            <button className="button button--ghost button--small" disabled={!connected || !m.whatsapp} onClick={() => test(m)}>
              {t('whatsapp.test')}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

const STATUS_LABEL: Record<OutgoingMessage['status'], MessageKey> = {
  pending: 'whatsapp.msg.pending',
  sent: 'whatsapp.msg.sent',
  failed: 'whatsapp.msg.failed',
};

function MessagesCard({ householdId }: { householdId: string }) {
  const { t } = useI18n();
  const showMessage = useMessage();
  const [messages, setMessages] = useState<OutgoingMessage[] | null>(null);

  const load = useCallback(() => {
    listOutgoingMessages(householdId)
      .then(setMessages)
      .catch((e: Error) => showMessage('error', e.message));
  }, [householdId, showMessage]);
  useEffect(load, [load]);

  return (
    <section className="card">
      <div className="card__header">
        <h2 className="card__title">{t('whatsapp.messagesTitle')}</h2>
        <button className="button button--ghost button--small" onClick={load}>
          {t('whatsapp.refresh')}
        </button>
      </div>
      <p className="muted small" style={{ marginBottom: 8 }}>
        {t('whatsapp.messagesHint')}
      </p>
      {!messages && <p className="muted">{t('common.loading')}</p>}
      {messages?.length === 0 && <p className="muted">{t('whatsapp.messagesEmpty')}</p>}
      <div className="list">
        {messages?.map((m) => (
          <div key={m.id} className="list-item">
            <div className="list-item__main">
              <div className="list-item__title">
                <span className={`pill wa-status wa-status--${m.status}`}>{t(STATUS_LABEL[m.status])}</span> {m.recipient_label}
                <span className="muted small"> · {shortDate(m.created_at.slice(0, 10))}</span>
              </div>
              <div className="list-item__sub wa-message__text">{m.text}</div>
              {m.last_error && m.status !== 'sent' && <div className="list-item__sub negative">{m.last_error}</div>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
