'use strict';

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
    players: React.PropTypes.array.isRequired,
    winner: React.PropTypes.number,  // player ID
    round: React.PropTypes.number,
    slot: React.PropTypes.number,
    onClick: React.PropTypes.func.isRequired
  },
  click: function(i) {
    this.props.onClick(this.props.round, this.props.slot, i, this.props.players[i].index);
  },
  render: function() {
    var players = this.props.players;
    var playerSpans = players.map((p, i) => <span onClick={() => this.click(i)}>{p ? p.name : '\u00a0'}</span>);
    var winner = this.props.winner;
    if (winner !== null && winner !== undefined) {
      players.forEach((p, i) => {
        if (p && p.index == winner) playerSpans[i] = <b>{playerSpans[i]}</b>;
      });
    }
    return (
      <div className="match">
        {playerSpans[0]}
        <br/>
        {playerSpans[1]}
      </div>
    );
  }
});

var Bracket = React.createClass({
  propTypes: {
    matches: React.PropTypes.array.isRequired,
    players: React.PropTypes.array.isRequired,
    winner: React.PropTypes.number,
    startRound: React.PropTypes.number,
    handleAdvancePlayer: React.PropTypes.func.isRequired
  },
  handleClick: function(round, slot, participant, playerId) {
    this.props.handleAdvancePlayer(playerId, round, slot);
  },
  render: function() {
    var {matches, players} = this.props;
    var startRound = this.props.startRound || 0;
    var rows = matches[0].map((match, idx) => {
      var row_cells = [];
      var factor = 1;
      for (var i = 0; i < matches.length; i++, factor *= 2) {
        if (idx % factor == 0) {
          var match = matches[i][idx / factor];
          var winner = i == matches.length - 1 ? this.props.winner : null;
          row_cells.push(<td className="match-cell" key={i} rowSpan={factor}>
            {i > 0 ? <div className="connector"></div> : null}
            <Match players={match.map(x => players[x])}
                   winner={winner}
                   round={i + startRound}
                   slot={idx/factor}
                   onClick={this.handleClick} />
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
  getInitialState: function() {
    return this.stateWithModifications([]);
  },
  addModification: function(playerId, fromRound, fromSlot) {
    var originalMatches = this.props.data.matches;
    var modifications = this.state.modifications;
    if (fromRound == originalMatches.length - 1) {
      modifications.push({winner: playerId});
    } else {
      modifications.push({playerId, toRound: 1 + fromRound});
    }
    this.setState(this.stateWithModifications(modifications));
  },
  resetModifications: function() {
    this.setState(this.stateWithModifications([]));
  },
  stateWithModifications: function(modifications) {
    console.log(modifications);
    var originalMatches = this.props.data.matches;
    var [newMatches, winner] = applyModificationsAndFill(originalMatches, modifications);
    return {
      modifications,
      matches: newMatches,
      winner
    };
  },
  render: function() {
    var players = this.props.data.players;
    var originalMatches = this.props.data.matches;
    var matches = this.state.matches;
    var winner = this.state.winner;
    players = updateRankings(players, matches, winner);
    return (
      <div>
        <button onClick={this.resetModifications}>Reset</button><br/>
        <Bracket matches={matches.slice(3)}
                 winner={winner}
                 players={players}
                 startRound={3}
                 handleAdvancePlayer={this.addModification} />
        <RankingTable players={players} />
      </div>
    );
  }
});

data.players.forEach((p, i) => { p.index = i; });
React.render(<Root data={data} />, document.getElementById('root'));
