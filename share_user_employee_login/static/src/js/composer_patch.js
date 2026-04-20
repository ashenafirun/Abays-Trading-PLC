import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Composer.prototype, {
    setup() {
        super.setup();

        this.employee_avatar = '';
        if (session.employee_id_login > 0 && session.employee_avatar !== '') {
             this.employee_avatar = session.employee_avatar;
        }
    },
});
