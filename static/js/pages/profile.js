new Vue({
    el: "#app",
    delimiters: ["<%", "%>"],
    data() {
        return {
            data: {
                stats: {
                    out: [{}],
                    load: true
                },
                grades: {},
                scores: {
                    recent: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    },
                    best: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    }
                },
                maps: {
                    most: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    }
                },
                status: {
                    out: [{}],
                    load: true
                }
            },
            mode: mode,
            mods: mods,
            modeasahi: 0,
            userid: userid
        };
    },
    created() {
        // starting a page
        this.mode = this.StrtoModeInt();
        this.LoadPlayerStatus();
        this.LoadAllofdata();
    },
    methods: {
        LoadAllofdata() {
            this.LoadMostBeatmaps();
            this.LoadProfileData();
            this.LoadScores('best');
            this.LoadScores('recent');
        },
        LoadProfileData() {
            this.$set(this.data.stats, 'load', true);
            this.$axios.get(`${window.location.protocol}//api.${domain}/player`, {
                    params: {
                        id: this.userid,
                        mode: this.StrtoModeInt(),
                        rx: this.StrtoModInt()
                    }
                })
                .then(res => {
                    this.$set(this.data.stats, 'out', res.data.stats);
                    this.data.stats.load = false;
                });
        },
        LoadPlayerStatus() {
            this.$set(this.data.status, 'load', true);
            this.$axios.get(`${window.location.protocol}//api.${domain}/player_status`, {
                params: {
                    id: this.userid
                }
            })
                .then(res => {
                    this.$set(this.data.status, 'out', res.data.status);
                    this.data.status.load = false;
                });
        },   
        LoadScores(sort) {
            this.$set(this.data.scores[`${sort}`], 'load', true);
            this.$axios.get(`${window.location.protocol}//api.${domain}/player_scores`, {
                    params: {
                        id: this.userid,
                        mode: this.StrtoModeInt(),
                        rx: this.StrtoModInt(),
                        type: sort,
                        limit: this.data.scores[`${sort}`].more.limit
                    }
                })
                .then(res => {
                    this.data.scores[`${sort}`].out = res.data.scores;
                    this.data.scores[`${sort}`].load = false
                    this.data.scores[`${sort}`].more.full = this.data.scores[`${sort}`].out.length != this.data.scores[`${sort}`].more.limit;
                });
        },
        LoadMostBeatmaps() {
            this.$set(this.data.maps.most, 'load', true);
            this.$axios.get(`${window.location.protocol}//api.${domain}/player_most_played`, {
                    params: {
                        id: this.userid,
                        mode: this.StrtoModeInt(),
                        limit: this.data.maps.most.more.limit,
                        rx: this.StrtoModInt()
                    }
                })
                .then(res => {
                    this.data.maps.most.out = res.data.maps;
                    this.data.maps.most.load = false;
                    this.data.maps.most.more.full = this.data.maps.most.out.length != this.data.maps.most.more.limit;
                });
        },
        ChangeModeMods(mode, mods) {
            if (window.event)
                window.event.preventDefault();

            this.mode = mode;
            this.mods = mods;

            this.modegulag = this.StrtoModeInt();
            this.data.scores.recent.more.limit = 5
            this.data.scores.best.more.limit = 5
            this.data.maps.most.more.limit = 6
            this.LoadAllofdata();
        },
        AddLimit(which) {
            if (window.event)
                window.event.preventDefault();

            if (which == 'bestscore') {
                this.data.scores.best.more.limit += 5;
                this.LoadScores('best');
            } else if (which == 'recentscore') {
                this.data.scores.recent.more.limit += 5;
                this.LoadScores('recent');
            } else if (which == 'mostplay') {
                this.data.maps.most.more.limit += 4;
                this.LoadMostBeatmaps();
            }
        },
        actionIntToStr(d) {
            switch (d[`action`]) {
                case 0:
                    return 'Idle: 🔍 Song Select';
                case 1:
                    return '🌙 AFK';
                case 2:
                    return `Playing: 🎶 ${d[`info`]}`;
                case 3:
                    return `Editing: 🔨 ${d[`info`]}`;
                case 4:
                    return `Modding: 🔨 ${d[`info`]}`;
                case 5:
                    return 'In Multiplayer: Song Select';
                case 6:
                    return `Watching: 👓 ${d[`info`]}`;
                    // 7 not used
                case 8:
                    return `Testing: 🎾 ${d[`info`]}`;
                case 9:
                    return `Submitting: 🧼 ${d[`info`]}`;
                    // 10 paused, never used
                case 11:
                    return 'Idle: 🏢 In multiplayer lobby';
                case 12:
                    return `In Multiplayer: Playing 🌍 ${d[`info`]} 🎶`;
                case 13:
                    return 'Idle: 🔍 Searching for beatmaps in osu!direct';
                default:
                    return 'Unknown: 🚔 not yet implemented!';
            }
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
        secondsToDhm(seconds) {
            seconds = Number(seconds);
            var dDisplay = `${Math.floor(seconds / (3600 * 24))}d `;
            var hDisplay = `${Math.floor(seconds % (3600 * 24) / 3600)}h `;
            var mDisplay = `${Math.floor(seconds % 3600 / 60)}m `;
            return dDisplay + hDisplay + mDisplay;
        },
        StrtoModeInt() {
            switch (this.mode) {
                case 'std':
                    return 0;
                case 'taiko':
                    return 1;
                case 'catch':
                    return 2;
                case 'mania':
                    return 3;
                default:
                    return 0;
            }
        },
        StrtoModInt() {
            switch (this.mods) {
                case 'vn':
                    return 0;
                case 'rx':
                    return 1;
                case 'ap':
                    return 2;
                default:
                    return 0;
            }
        },
    },
    computed: {}
});