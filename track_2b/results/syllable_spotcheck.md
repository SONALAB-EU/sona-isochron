# Syllable counter spot check

- Date: 2026-10-09 10:38 UTC
- Git commit: d67d9c76e46a047d24b8b39724ab825c0e348911
- Counter: eSpeak NG text-to-speech: 1.52.0, syllabic nuclei in its IPA output (`isochron.metrics.length.syllables`), next to the vowel-group heuristic
- Sentences: FLEURS train (revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`) containing digits, 5 per language drawn with seed 0
- Model, endpoint, TTS: none
- n: 40 words, 10 sentences

Reference: hand counts by Claude (standard pronunciation, Duden for German), not yet checked by a native speaker.

## Accuracy against the reference

- espeak-ng: 46/50 items exact (92 %)
- heuristic: 21/50 items exact (42 %)

espeak-ng misses:

- naiv: espeak-ng 1, reference 2
- Zoologie: espeak-ng 3, reference 4
- Melodien: espeak-ng 3, reference 4
- de sentence 421: espeak-ng 24, reference 25

## DE words

| Word | Reference | espeak-ng | Heuristic | espeak-ng IPA |
|------|----------:|----------:|----------:|---------------|
| Haus | 1 | 1 | 1 | `h_ˈaʊ_s` |
| Fenster | 2 | 2 | 2 | `f_ˈɛ_n_s_t_ɜ` |
| Mädchen | 2 | 2 | 2 | `m_ˈɛː_d_ç_ə_n` |
| Schifffahrt | 2 | 2 | 2 | `ʃ_ˈɪ_f_ɑː_ɾ_t` |
| Theater | 3 | 3 | 2 | `t_eː_ˈɑː_t_ɜ` |
| Eier | 2 | 2 | 1 | `_ˈaɪ_ɜ` |
| Bauer | 2 | 2 | 1 | `b_ˈaʊ_ɜ` |
| Uhr | 1 | 1 | 1 | `_ˈuː_ɾ` |
| Museum | 3 | 3 | 2 | `m_uː_z_ˈeː_ʊ_m` |
| beobachten | 4 | 4 | 3 | `b_ə__ˈoː_b_a_x_t_ə_n` |
| Familie | 3 | 3 | 3 | `f_a_m_ˈiː_l_ɪ__ə` |
| Linien | 2 | 2 | 2 | `l_ˈiː_n_ɪ__ə_n` |
| Region | 2 | 2 | 2 | `r_ˌeː_ɡ_i__ˈoː_n` |
| Studium | 2 | 2 | 2 | `ʃ_t_ˈuː_d_iː_ˌʊ_m` |
| Ruine | 3 | 3 | 2 | `r_uː_ˈiː_n_ə` |
| Poesie | 3 | 3 | 2 | `p_ˌoː_eː_z_ˈiː` |
| Kakao | 3 | 3 | 2 | `k_ˈɑ_k_a_ˌoː` |
| naiv | 2 | 1 | 1 | `n_ˈaɪ_f` |
| Zoologie | 4 | 3 | 3 | `ts_ˌoː_l_oː_ɡ_ˈiː` |
| Melodien | 4 | 3 | 3 | `m_eː_l_ˈoː_d_ɪ__ə_n` |

## DE sentences with digits

| FLEURS id | Reference | espeak-ng | Heuristic | Sentence | espeak-ng IPA |
|----------:|----------:|----------:|----------:|----------|---------------|
| 860 | 51 | 51 | 50 | In einigen Ländern gibt es selbst für erstmalige Vergehen überaus drakonische Strafen; diese können Gefängnisstrafen von über 10 Jahren oder die Todesstrafe einschließen. | `_ɪ_n _ˈaɪ_n_ɪ_ɡ_ə_n l_ˈɛ_n_d_ɜ_n ɡ_ˈiː_p_t _ɛ_s z_ˈɛ_l_p_s_t__ f_yː_ɾ _ˈɛ_ɾ_s_t_m_ˌɑ_l_ɪ_ɡ_ə f_ɛ_ɾ_ɡ_ˈeː_ə_n_ _ˌyː_b_ɜ__ˌaʊ_s d_ɾ_a_k_ˈoː_n_ɪ_ʃ_ə ʃ_t_ɾ_ˈɑː_f_ə_n d_ˌiː_z_ə k_ˌœ_n_ə_n ɡ_ə_f_ˈɛ_ŋ_n_ɪ_s_ʃ_t_ɾ_ˌɑː_f_ə_n_ f_ɔ_n__ _ˌyː_b_ɜ ts_ˈeː_n j_ˈɑː_r_ə_n__ _ˌoː_d_ɜ d_iː t_ˈoː_d_ɛ_s_ʃ_t_ɾ_ˌɑː_f_ə _ˈaɪ_n_ʃ_l_ˌiː_s_ə_n` |
| 1048 | 40 | 40 | 32 | Er machte eine Ausbildung als Entbindungsarzt und nahm 1959 seine Arbeit im National Women's Hospital in Auckland auf. | `_ɛ_ɾ m_ˈa_x_t_ə _ˌaɪ_n_ə _ˈaʊ_s_b_ˌɪ_l_d_ʊ_ŋ_ _a_l_s _ɛ_n_t_b_ˈɪ_n_d_ʊ_ŋ_s__ˌa_ɾ_ts_t__ _ʊ_n_t n_ˈɑː_m n_ˈɔø_n_ts_eː_n h_ˈʊ_n_d_ɜ_t n_ˈɔø_n _ʊ_n_t_f_ˈʏ_n_f_ts_ɪ_ç z_ˌaɪ_n_ə _ˈa_ɾ_b_aɪ_t_ _ɪ_m n_a_ts_j_ˌoː_n_ˈɑː_l v_ˈoː_m_eː_n_s__ h_ˌɔ_s_p_iː_t_ˈɑː_l_ _ɪ_n _ˈaʊ_k_l_a_n_t _ˈaʊ_f` |
| 45 | 68 | 68 | 62 | Fred ist der stärkste tropische Wirbelsturm, der seit dem Einsatz von Satellitenbildern jemals so weit südlich und östlich im Atlantik aufgezeichnet wurde, und erst der dritte größere Wirbelsturm, der östlich von 35°W registriert wurde. | `f_r_ˈeː_t _ɪ_s_t d_ɛ_ɾ ʃ_t_ˈɛ_ɾ_k_s_t_ə t_ɾ_ˈoː_p_ɪ_ʃ_ə v_ˈɪ_ɾ_b_ə_l_s_t_ˌʊɐ_m d_ɛ_ɾ z_aɪ_t d_eː_m _ˈaɪ_n_z_ˌa_ts_ f_ɔ_n z_ˈɑ_t_ə_l_ˌiː_t_ə_n_b_ˌɪ_l_d_ɜ_n j_ˈeː_m_ɑː_l_s z_oː v_ˈaɪ_t z_ˈyː_t_l_ɪ_ç__ _ʊ_n_t _ˈœ_s_t_l_ɪ_ç_ _ɪ_m _a_t_l_ˈa_n_t_iː_k _ˈaʊ_f_ɡ_ə_ts_ˌaɪ_ç_n_ə_t v_ˌʊɐ_d_ə _ʊ_n_t _ˈeː_ɾ_s_t d_ɛ_ɾ d_ɾ_ˈɪ_t_ə ɡ_ɾ_ˈøː_s_ə_r_ə v_ˈɪ_ɾ_b_ə_l_s_t_ˌʊɐ_m d_ɛ_ɾ _ˈœ_s_t_l_ɪ_ç_ f_ɔ_n f_ˈʏ_n_f _ʊ_n_t_d_ɾ_ˈaɪ_s_ɪ_ç ɡ_ɾ_ˈɑː_t v_ˈeː r_ˌeː_ɡ_ɪ_s_t_ɾ_ˈiː_ɾ_t v_ˌʊɐ_d_ə` |
| 421 | 25 | 24 | 22 | Um das 15. Jahrhundert stand Nordestland unter großem kulturellen Einfluss aus Deutschland. | `_ʊ_m d_a_s f_ˈʏ_n_f_ts_eː_n j_ɑː_ɾ_h_ˈʊ_n_d_ɜ_t ʃ_t_ˈa_n_t n_ˈɔ_ɾ_d_ɛ_s_t_l_ˌa_n_t__ _ˌʊ_n_t_ɜ ɡ_ɾ_ˈoː_s_ə_m k_ˌʊ_l_t_uː_r_ˈɛ_l_ə_n _ˈaɪ_n_f_l_ˌʊ_s_ _ˌaʊ_s d_ˈɔø_t_ʃ_l_a_n_t` |
| 1320 | 50 | 50 | 38 | Die Südlichen Shetlandinseln, die 1819 entdeckt wurden, werden von mehreren Ländern beansprucht und haben die meisten Stationen. 2020 waren sechzehn aktiv. | `d_iː z_ˈyː_t_l_ɪ_ç_ə_n ʃ_ˈɛ_t_l_a_n_d_ˌɪ_n_z_ə_l_n d_iː _ˈa_x_ts_eː_n h_ˈʊ_n_d_ɜ_t n_ˈɔø_n_ts_eː_n _ɛ_n_t_d_ˈɛ_k_t v_ˌʊɐ_d_ə_n v_ˌɛ_ɾ_d_ə_n_ f_ɔ_n m_ˈeː_r_ə_r_ə_n l_ˈɛ_n_d_ɜ_n b_ə_ˈa_n_ʃ_p_ɾ_ˌʊ_x_t__ _ʊ_n_t h_ˌɑː_b_ə_n d_iː m_ˈaɪ_s_t_ə_n ʃ_t_a_ts_j_ˈoː_n_ə_n ts_v_ˈaɪ t_ˈaʊ_z_ə_n_t ts_v_ˈa_n_ts_ɪ_ç v_ɑː_r_ə_n z_ˈɛ_ç_ts_eː_n _a_k_t_ˈiː_f` |

## FR words

| Word | Reference | espeak-ng | Heuristic | espeak-ng IPA |
|------|----------:|----------:|----------:|---------------|
| aéroport | 4 | 4 | 3 | `a_e_ʁ_o_p_ˈɔ_ʁ` |
| pays | 2 | 2 | 1 | `p_ɛ_ˈi` |
| oiseau | 2 | 2 | 2 | `w_a_z_ˈo` |
| petite | 2 | 2 | 2 | `p_ə_t_ˈi_t` |
| théâtre | 2 | 2 | 1 | `t_e_ˈaː_t_ʁ` |
| poème | 2 | 2 | 1 | `p_ɔ_ˈɛ_m` |
| Noël | 2 | 2 | 1 | `n_ɔ_ˈɛ_l` |
| ouest | 1 | 1 | 1 | `w_ˈɛ_s_t` |
| maïs | 2 | 2 | 1 | `m_a_ˈi_s` |
| réaliser | 4 | 4 | 3 | `ʁ_e_a_l_i_z_ˈe` |
| mademoiselle | 3 | 3 | 4 | `m_a_d_m_w_a_z_ˈɛ_l` |
| cahier | 2 | 2 | 2 | `k_a_j_ˈe` |
| hier | 1 | 1 | 1 | `_j_ˈɛ_ʁ` |
| lion | 1 | 1 | 1 | `l_j_ˈɔ̃` |
| école | 2 | 2 | 2 | `e_k_ˈɔ_l` |
| nuit | 1 | 1 | 1 | `n_y_ˈi` |
| depuis | 2 | 2 | 2 | `d_ə_p_y_ˈi` |
| cuisine | 2 | 2 | 2 | `k_y_i_z_ˈi_n` |
| aujourd'hui | 3 | 3 | 3 | `o_ʒ_u_ʁ_d_y_ˈi` |
| juillet | 2 | 2 | 2 | `ʒ_y_i_j_ˈɛ` |

## FR sentences with digits

| FLEURS id | Reference | espeak-ng | Heuristic | Sentence | espeak-ng IPA |
|----------:|----------:|----------:|----------:|----------|---------------|
| 1221 | 42 | 42 | 36 | Les paralympiques se tiendront du 24 août au 5 septembre 2021. Certains événements se tiendront dans d’autres localisations à travers le Japon. | `l_e- p_a_ʁ_a_l_ɛ̃_p_ˈi_k s_ə- t_j_ɛ̃_d_ʁ_ˈɔ̃ d_y- v_ɛ̃_t_k_ˈa_t_ʁ ˈu_t o s_ˈɛ̃_k s_ɛ_p_t_ˈɑ̃_b_ʁ d_ø m_i_l v_ɛ̃_t_e_ˈœ̃ s_ɛ_ʁ_t_ˈɛ̃_z e_v_e_n_m_ˈɑ̃ s_ə- t_j_ɛ̃_d_ʁ_ˈɔ̃ d_ɑ̃ d_o_t_ʁ l_o_k_a_l_i_z_a_s_j_ˈɔ̃_z a t_ʁ_a_v_ˈɛ_ʁ l_ə- ʒ_a_p_ˈɔ̃` |
| 1013 | 43 | 43 | 40 | L'Indonésie comptant 17 000 îles, la cuisine indonésienne est un terme générique qui couvre une grande variété de cuisines régionales présentes dans tout le pays. | `l_ɛ̃_d_o_n_e_z_ˈi k_ɔ̃_t_ˈɑ̃ d_i_s_ɛ_t m_ˈi_l ˈi_l l_a- k_y_i_z_ˈi_n ɛ̃_d_o_n_e_z_j_ˈɛ_n ɛ_t œ̃ t_ˈɛ_ʁ_m ʒ_e_n_e_ʁ_ˈi_k k_i k_ˈu_v_ʁ y_n ɡ_ʁ_ˈɑ̃_d v_a_ʁ_j_e_t_ˈe d_ə- k_y_i_z_ˈi_n ʁ_e_ʒ_j_o_n_ˈa_l p_ʁ_e_z_ˈɑ̃_t d_ɑ̃ t_u l_ə- p_ɛ_ˈi` |
| 478 | 49 | 49 | 44 | Alexandre, en tant que roi, offrit de payer pour reconstruire le temple, mais son offre fut déclinée. Plus tard, après la mort d’Alexandre, le temple fut reconstruit en 323 avant notre ère. | `a_l_ɛ_k_s_ˈɑ̃_d_ʁ ɑ̃ t_ɑ̃ k_ə ʁ_w_ˈa ɔ_f_ʁ_ˈi d_ə- p_ɛ_j_ˈe p_u_ʁ ʁ_ə_k_ɔ̃_s_t_ʁ_y_ˈi_ʁ l_ə- t_ˈɑ̃_p_l m_ɛ s_ɔ̃_n ˈɔ_f_ʁ f_ˈy d_e_k_l_i_n_ˈe p_l_y t_ˈa_ʁ a_p_ʁ_ˌɛ l_a- m_ˈɔ_ʁ d_a_l_ɛ_k_s_ˈɑ̃_d_ʁ l_ə- t_ˈɑ̃_p_l f_ˈy ʁ_ə_k_ɔ̃_s_t_ʁ_y_ˈi_ ɑ̃ t_ʁ_w_a_s_ɑ̃ v_ɛ̃_t_t_ʁ_w_ˈa_z a_v_ˌɑ̃ n_o_t_ʁ ˈɛ_ʁ` |
| 1189 | 44 | 44 | 26 | Le bras principal du Fleuve Amazone est long de 6 387 km (3 980 miles). Il collecte l'eau des milliers de petites rivières. | `l_ə- b_ʁ_ˈa p_ʁ_ɛ̃_s_i_p_ˈa_l d_y- f_l_ˈø_v a_m_a_z_ˈo_n ɛ l_ˈɔ̃ d_ə- s_i m_ˈi_l_ t_ʁ_w_a_s_ɑ̃ k_a_t_ʁ_ə_v_ɛ̃_s_ˈɛ_t k_i_l_o_m_ˈɛ_t_ʁ__ t_ʁ_w_a m_ˈi_l_ n_œ_f_s_ɑ̃ k_a_t_ʁ_ə_v_ˈɛ̃ m_ˈi_l i_l k_ɔ_l_ˈɛ_k_t l_ˈo d_e- m_i_l_j_ˈe d_ə- p_ə_t_ˈi_t ʁ_i_v_j_ˈɛ_ʁ` |
| 713 | 30 | 30 | 26 | Plus de 60 bateaux de croisière sillonnent les eaux des Galápagos, dont la taille varie de 8 à 100 passagers. | `p_l_y d_ə- s_w_a_s_ˈɑ̃_t b_a_t_ˈo d_ə- k_ʁ_w_a_z_j_ˈɛ_ʁ s_i_j_ˈɔ_n l_e-_z ˈo d_e- ɡ_a_l_a_p_a_ɡ_ˈo d_ɔ̃ l_a- t_ˈa_j v_a_ʁ_ˈi d_ə- _y_ˈi_t a s_ˈɑ̃ p_a_s_a_ʒ_ˈe` |
