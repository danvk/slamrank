var expect = chai.expect;

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
  });
});
