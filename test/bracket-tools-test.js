var expect = chai.expect;
chai.config.truncateThreshold = 0; // disable truncating

describe('bracket-tools', function() {
  describe('applyModifications', function() {
    var matches = [
      // Quarterfinals
      [
        [0, 7],
        [3, 4],
        [2, 5],
        [1, 6]
      ],
      // Semifinals
      [
        [0, 3],
        [2, 1]
      ],
      // Finals
      [
        [0, 1]
      ]
    ];

    it('should change the winner', function() {
      var mods = [{winner: 1}];
      var [newMatches, winner] = applyModifications(matches, mods);
      expect(winner).to.equal(1);
      expect(newMatches).to.deep.equal(matches);  // no change
    });

    it('should remove losers', function() {
      var mods = [{playerId: 7, toRound: 1}];  // knock out the top seed
      var [newMatches, winner] = applyModifications(matches, mods);
      expect(winner).to.equal(-1);
      expect(newMatches).to.deep.equal([
        matches[0],  // Quarters are unchanged
        [
          [7, 3],  // Player 7 advances
          [2, 1]
        ],
        [
          [null, 1]  // The top seed leaves a gap
        ]
      ]);
    });
  });

  describe('applyModificationsAndFill', function() {
    var matches = [
      // Quarterfinals
      [
        [0, 7],
        [3, 4],
        [2, 5],
        [1, 6]
      ],
      // Semifinals
      [
        [null, null],
        [null, null]
      ],
      // Finals
      [
        [null, null]
      ]
    ];

    it('should change the winner', function() {
      // The user sees all the top-seeds winning. They click the #2 player in
      // the final to make him the winner.
      var mods = [{winner: 1}];
      var [newMatches, winner] = applyModificationsAndFill(matches, mods);
      expect(winner).to.equal(1);
      expect(newMatches).to.deep.equal([
          matches[0], 
          [
            [0, 3],
            [2, 1]
          ],
          [
            [0, 1]
          ]]);
    });
  });
});
