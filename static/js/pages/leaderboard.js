new Vue({
    el: "#app",
    delimiters: ["<%", "%>"],
    data() {
        return {
            flags: window.flags,
            boards : {},
            mode : 'std',
            mods : 'vn',
            load : false,
            no_player : false, // soon
        };
    },
    created() {
        this.LoadData(mode, mods, sort);
        this.LoadLeaderboard(sort, mode, mods);
    },
    methods: {
        LoadData(mode, mods) {
            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
        },
        LoadLeaderboard(mode, mods) {
            if (window.event)
                window.event.preventDefault();
            
            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
            this.$set(this, 'load', true);
            window.history.replaceState('', document.title, `/leaderboard/${this.mode}/${this.mods}`);
            this.$axios.get(`${window.location.protocol}//api.${domain}/get_leaderboard`, { params: {
                mode: this.StrtoModeInt(),
                rx: this.StrtoModInt()
            }}).then(res => {
                this.boards = res.data;
                this.$set(this, 'load', false);
            });
        },
        scoreFormat(score) {
            var addCommas = this.addCommas;
            if (score > 1000 * 1000) {
                if (score > 1000 * 1000 * 1000)
                    return `${addCommas((score / 1000000000).toFixed(2))} billion`;
                return `${addCommas((score / 1000000).toFixed(2))} million`;
            }
            return addCommas(score);
        },
        addCommas(nStr) {
            nStr += '';
            var x = nStr.split('.');
            var x1 = x[0];
            var x2 = x.length > 1 ? '.' + x[1] : '';
            var rgx = /(\d+)(\d{3})/;
            while (rgx.test(x1)) {
                x1 = x1.replace(rgx, '$1' + ',' + '$2');
            }
            return x1 + x2;
        },
        StrtoModeInt() {
            switch (this.mode) {
                case 'std': return 0;
                case 'taiko': return 1;
                case 'catch': return 2;
                case 'mania': return 3;
                default: return 0;
            }
        },
        StrtoModInt() {
            switch (this.mods) {
                case 'vn': return 0;
                case 'rx': return 1;
                case 'ap': return 2;
                default: return 0;
            }
        },
    },
    computed: {}
});
