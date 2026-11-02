import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listMembers } from '../api/households';
import type { Member } from '../api/types';
import { PixPayModal, PixReceiver } from '../components/PixPayModal';
import { meAsReceiver, memberAsReceiver } from '../components/pixReceivers';
import { TopBar } from '../components/TopBar';
import { lastHousehold, useAuth } from '../contexts/AuthContext';
import { useI18n } from '../i18n';
import { formatMoney, parseAmount } from '../utils/format';

const ME = 'me';

/** Tool: a PIX QR code + copy-and-paste code for any amount, using the same sheet as the split table. */
export function PixGenPage() {
  const { me } = useAuth();
  const { t } = useI18n();
  const householdId = lastHousehold() || me?.households[0]?.id;
  const household = me?.households.find((h) => h.id === householdId);

  const [members, setMembers] = useState<Member[]>([]);
  const [receiverId, setReceiverId] = useState<string>(ME);
  const [amountText, setAmountText] = useState('');
  const [error, setError] = useState('');
  const [shown, setShown] = useState<{ receiver: PixReceiver; amount: number } | null>(null);

  // Other people from the current household can be picked as receiver too
  useEffect(() => {
    if (!householdId) return;
    listMembers(householdId)
      .then((list) => setMembers(list.filter((m) => m.is_active && m.user_id !== me?.id)))
      .catch(() => setMembers([]));
  }, [householdId, me?.id]);

  const receiver = useMemo((): PixReceiver | null => {
    if (!me) return null;
    if (receiverId === ME) return meAsReceiver(me);
    const member = members.find((m) => m.id === receiverId);
    return member && householdId ? memberAsReceiver(householdId, member) : null;
  }, [me, receiverId, members, householdId]);

  const amount = parseAmount(amountText);
  const missingKey = receiver && !(receiver.bankInfoType === 'pix' && receiver.bankInfo);

  const generate = (e: FormEvent) => {
    e.preventDefault();
    if (!(amount > 0)) return setError(t('validation.amountPositive'));
    if (Math.round(amount * 100) / 100 !== amount) return setError(t('validation.twoDecimals'));
    if (!receiver) return setError(t('pixgen.pickReceiver'));
    setError('');
    setShown({ receiver, amount });
  };

  return (
    <>
      <TopBar householdId={householdId} householdName={household?.name} canManage={household?.role === 'manager' || me?.is_admin} />
      <main className="page">
        <div className="page__inner page__inner--narrow">
          <div>
            <Link to="/tools" className="muted small">
              ← {t('tools.title')}
            </Link>
            <h1 className="page-title">{t('pixgen.title')}</h1>
            <p className="page-description">{t('pixgen.description')}</p>
          </div>

          <form className="card" onSubmit={generate} noValidate>
            <div className="form-field">
              <label className="form-label" htmlFor="pix-amount">
                {t('cost.amount', { currency: 'BRL' })}
              </label>
              <input
                id="pix-amount"
                className="form-input form-input--amount"
                inputMode="decimal"
                placeholder="0.00"
                value={amountText}
                onChange={(e) => setAmountText(e.target.value)}
                autoComplete="off"
                autoFocus
              />
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="pix-receiver">
                {t('pixgen.receiver')}
              </label>
              <select id="pix-receiver" className="form-select" value={receiverId} onChange={(e) => setReceiverId(e.target.value)}>
                <option value={ME}>{t('pixgen.me', { name: me?.display_name || '' })}</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                    {m.bank_info_type === 'pix' && m.bank_info ? '' : ` ${t('pixgen.noKeyMark')}`}
                  </option>
                ))}
              </select>
              {missingKey && (
                <span className="form-hint">
                  {receiverId === ME ? (
                    <>
                      {t('pixgen.noOwnKey')} <Link to="/account">{t('pixgen.addInAccount')}</Link>
                    </>
                  ) : (
                    t('pixgen.noKeyOther')
                  )}
                </span>
              )}
            </div>

            {error && (
              <p className="form-error" role="alert" style={{ marginBottom: 12 }}>
                {error}
              </p>
            )}
            <button className="button button--primary button--large button--block">
              {amount > 0 ? t('pixgen.generateFor', { amount: formatMoney(amount, 'BRL') }) : t('pixgen.generate')}
            </button>
          </form>
        </div>
      </main>

      {shown && (
        <PixPayModal
          receiver={shown.receiver}
          amount={shown.amount}
          currency="BRL"
          subtitle={t('pay.title', { name: shown.receiver.name })}
          onClose={() => setShown(null)}
        />
      )}
    </>
  );
}
