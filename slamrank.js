// Replace all "null" entries with the higher-ranked player
function fillBracket(matches) {
  var matches = JSON.parse(JSON.stringify(matches));
  for (var i = 1; i < matches.length; i++) {
    var match_list = matches[i];
    for (var j = 0; j < match_list.length; j++) {
      for (var k = 0; k < 2; k++) {
        if (match_list[j][k] == null) {
          var prev_match = matches[i-1][j * 2 + k];
          match_list[j][k] = Math.min(prev_match[0], prev_match[1]);
        }
      }
    }
  }
  return matches;
}

// Number of ranking points you earn for getting to each round.
var ROUND_POINTS = [
  10,
  45,
  90,
  180,
  360,
  720,
  1200,
  2000
];

// Returns a list of new point values for each player
function playerPoints(matches) {
  var points = new Array(128);
  matches.forEach((match_list, round_idx) => {
    match_list.forEach(match => {
      var [p1, p2] = match;
      if (p1 !== null) points[p1] = ROUND_POINTS[round_idx];
      if (p2 !== null) points[p2] = ROUND_POINTS[round_idx];
    });
  });
  return points;
}

// Add "next week" data to the ranking table in light of tourney results.
// This adds points_gaining, new_points and new_rank fields.
function updateRankings(players, matches) {
  var players = JSON.parse(JSON.stringify(players));
  var points = playerPoints(matches);
  players.forEach((p, i) => {
    p.points_gaining = points[i];
    p.new_points = p.points - p.points_dropping + p.points_gaining;
  });

  var point_indices = _.chain(players)
                       .map((p, i) => [p.new_points, i])
                       .sortBy(x => -x[0])
                       .map((x, i) => [x[1], 1 + i])
                       .object()
                       .value();

  players.forEach((p, i) => {
    p.new_rank = point_indices[i];
  });

  return players;
}

var RankingRow = React.createClass({
  render: function() {
    var player = this.props.player;
    return (
      <tr>
        <td>{player.rank}</td>
        <td>{player.name}</td>
        <td>{player.points}</td>
        <td>{player.points_dropping}</td>
        <td>{player.points_gaining}</td>
        <td>{player.new_points}</td>
        <td>{player.new_rank}</td>
      </tr>
    );
  }
});

var RankingTable = React.createClass({
  render: function() {
    var players = this.props.players;
    return (
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Player</th>
            <th>Points</th>
            <th>Dropping</th>
            <th>Gaining</th>
            <th>New Pts</th>
            <th>New Rank</th>
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => <RankingRow player={p} key={i} />)}
        </tbody>
      </table>
    );
  }
});

var Match = React.createClass({
  propTypes: {
    players: React.PropTypes.array.isRequired
  },
  render: function() {
    var players = this.props.players;
    return (
      <div className="match">
        {players[0] ? players[0].name : '\u00a0'}<br/>
        {players[1] ? players[1].name : '\u00a0'}
      </div>
    );
  }
});

var Bracket = React.createClass({
  propTypes: {
    matches: React.PropTypes.array.isRequired,
    players: React.PropTypes.array.isRequired
  },
  render: function() {
    var {matches, players} = this.props;
    var rows = matches[0].map((match, idx) => {
      var row_cells = [];
      var factor = 1;
      for (var i = 0; i < matches.length; i++, factor *= 2) {
        if (idx % factor == 0) {
          var match = matches[i][idx / factor];
          row_cells.push(<td className="match-cell" key={i} rowSpan={factor}>
            {i > 0 ? <div className="connector"></div> : null}
            <Match players={match.map(x => players[x])} />
          </td>);
        }
      }

      return <tr key={idx}>{row_cells}</tr>;
    });

    return (
      <table><tbody>{rows}</tbody></table>
    );
  }
});

var Root = React.createClass({
  propTypes: {
    data: React.PropTypes.object.isRequired
  },
  render: function() {
    var players = this.props.data.players;
    var matches = this.props.data.matches;
    matches = fillBracket(matches);
    players = updateRankings(players, matches);
    return (
      <div>
        <Bracket matches={matches.slice(3)} players={players} />
        <RankingTable players={players} />
      </div>
    );
  }
});

React.render(<Root data={data} />, document.getElementById('root'));
