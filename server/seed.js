const db = require('./db');

const WEEK_OF = '2026-09-20';

const microcycle = {
  weekOf: WEEK_OF,
  programs: [
    {
      day: 1,
      id: 'sess_upper',
      name: 'Session A — Shoulder + Upper',
      blocks: [
        {
          id: 'blk_upper',
          name: 'Upper',
          notes: 'Decline curl first — loads the scapula, makes bench feel better.',
          exercises: [
            { id: 'ex_decline_curl', name: 'Decline biceps curl', sets: 3, cue: 'Full stretch at bottom.', start_weight_lbs: 20 },
            { id: 'ex_bench', name: 'Bench press', sets: 3, cue: 'Upper back already loaded from curls. Use it.', start_weight_lbs: 135 },
            { id: 'ex_ohp', name: 'Barbell overhead press', sets: 3, cue: 'Full lockout. Elbows forward at bottom.', start_weight_lbs: 65 },
            { id: 'ex_landmine', name: 'Kneeling landmine press', sets: 3, cue: 'One side at a time. Tall kneeling, press on diagonal.', start_weight_lbs: 45 },
            { id: 'ex_lateral', name: 'Lateral raise', sets: 3, cue: 'Light. Full range — hip to ear height.', start_weight_lbs: 10 }
          ]
        },
        {
          id: 'blk_sled',
          name: 'Sled',
          notes: '6 lengths forward, 2 reverse.',
          exercises: [
            { id: 'ex_sled_fwd', name: 'Sled drag — forward', sets: 6, cue: '3 plates. One length per set.', start_weight_lbs: 135 },
            { id: 'ex_sled_rev', name: 'Sled drag — reverse', sets: 2, cue: '3 plates.', start_weight_lbs: 135 }
          ]
        }
      ]
    },
    {
      day: 3,
      id: 'sess_half_upper',
      name: 'Session B — Half Upper',
      blocks: [
        {
          id: 'blk_upper_b',
          name: 'Upper — condensed',
          notes: 'Half session. Quality over quantity.',
          exercises: [
            { id: 'ex_ohp_b', name: 'Barbell overhead press', sets: 3, cue: 'Full lockout.', start_weight_lbs: 65 },
            { id: 'ex_landmine_b', name: 'Kneeling landmine press', sets: 2, cue: 'One side at a time.', start_weight_lbs: 45 },
            { id: 'ex_lateral_b', name: 'Lateral raise', sets: 2, cue: 'Light. Full range.', start_weight_lbs: 10 }
          ]
        },
        {
          id: 'blk_sled_b',
          name: 'Sled',
          notes: '6 lengths forward, 2 reverse.',
          exercises: [
            { id: 'ex_sled_fwd_b', name: 'Sled drag — forward', sets: 6, cue: '3 plates.', start_weight_lbs: 135 },
            { id: 'ex_sled_rev_b', name: 'Sled drag — reverse', sets: 2, cue: '3 plates.', start_weight_lbs: 135 }
          ]
        }
      ]
    },
    {
      day: 4,
      id: 'sess_legs',
      name: 'Legs',
      blocks: [
        {
          id: 'blk_legs',
          name: 'Legs',
          notes: 'Crane airplanes are hard — they should be.',
          exercises: [
            { id: 'ex_leg_press', name: 'Single leg press', sets: 3, cue: 'Weak side first. Full range.', start_weight_lbs: 90 },
            { id: 'ex_step_up', name: 'Step up', sets: 3, cue: 'Drive through heel.', start_weight_lbs: 25 },
            { id: 'ex_crane', name: 'Crane airplanes', sets: 3, cue: 'Control the descent.', start_weight_lbs: 0 },
            { id: 'ex_lateral_c', name: 'Lateral raise', sets: 2, cue: 'Light. Full range.', start_weight_lbs: 10 }
          ]
        },
        {
          id: 'blk_sled_c',
          name: 'Sled',
          notes: '6 lengths forward, 2 reverse.',
          exercises: [
            { id: 'ex_sled_fwd_c', name: 'Sled drag — forward', sets: 6, cue: '3 plates.', start_weight_lbs: 135 },
            { id: 'ex_sled_rev_c', name: 'Sled drag — reverse', sets: 2, cue: '3 plates.', start_weight_lbs: 135 }
          ]
        }
      ]
    },
    {
      day: 5,
      id: 'sess_deadlift',
      name: 'Deadlifts',
      blocks: [
        {
          id: 'blk_dl',
          name: 'Deadlift',
          notes: 'Heavy first while fresh. Speed work after.',
          exercises: [
            { id: 'ex_dl_heavy', name: 'Deadlift — heavy', sets: 5, cue: '405. 1-2 reps per set. Full reset between reps.', start_weight_lbs: 405 },
            { id: 'ex_dl_speed', name: 'Deadlift — speed', sets: 4, cue: '315. Fast off the floor. Bar stays close.', start_weight_lbs: 315 },
            { id: 'ex_lateral_d', name: 'Lateral raise', sets: 2, cue: 'Light. Full range.', start_weight_lbs: 10 }
          ]
        },
        {
          id: 'blk_sled_d',
          name: 'Sled',
          notes: '6 lengths forward, 2 reverse.',
          exercises: [
            { id: 'ex_sled_fwd_d', name: 'Sled drag — forward', sets: 6, cue: '3 plates.', start_weight_lbs: 135 },
            { id: 'ex_sled_rev_d', name: 'Sled drag — reverse', sets: 2, cue: '3 plates.', start_weight_lbs: 135 }
          ]
        }
      ]
    }
  ]
};

db.prepare(`
  INSERT OR REPLACE INTO microcycles (week_of, data) VALUES (?, ?)
`).run(WEEK_OF, JSON.stringify(microcycle));

console.log(`Seeded microcycle for week ${WEEK_OF}`);
