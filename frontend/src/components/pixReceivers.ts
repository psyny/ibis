import { getMember } from '../api/households';
import type { Me, Member } from '../api/types';
import type { PixReceiver } from './PixPayModal';

/** A household member as a PIX receiver (their uploaded QR image is fetched only if needed). */
export function memberAsReceiver(householdId: string, member: Member): PixReceiver {
  return {
    name: member.display_name,
    bankInfoType: member.bank_info_type,
    bankInfo: member.bank_info,
    loadUploadedQr: member.has_transfer_qr
      ? () => getMember(householdId, member.id).then((m) => m.transfer_qr)
      : undefined,
  };
}

/** The signed-in user as a PIX receiver. */
export function meAsReceiver(me: Me): PixReceiver {
  return {
    name: me.display_name,
    bankInfoType: me.bank_info_type,
    bankInfo: me.bank_info,
    uploadedQr: me.transfer_qr,
  };
}
