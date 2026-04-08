import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    isSquashed(msg, prevMsg) {
        let val = super.isSquashed(msg, prevMsg);

        if (val) {
            if (msg.employee_id !== prevMsg.employee_id) {
                return false;
            }
        }
        return val;
    },

});
