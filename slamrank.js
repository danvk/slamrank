var RankingRow = React.createClass({
  render: function() {
    var player = this.props.player;
    return (
      <tr>
        <td>{player.rank}</td>
        <td>{player.name}</td>
        <td>{player.points}</td>
        <td>{player.points_dropping}</td>
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

// React.render(<RankingTable players={data.players} />, document.getElementById('root'));
React.render(<Bracket matches={data.matches.slice(3)} players={data.players} />, document.getElementById('root'));
