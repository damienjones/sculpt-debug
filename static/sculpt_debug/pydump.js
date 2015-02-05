$(document).on(
	{
		'click': function (e) {
			e.preventDefault();
			e.stopPropagation();

			var t = $(this);
			if (t.hasClass('sc_dbg_disabled'))
			{
				t.removeClass('sc_dbg_disabled');
				t.next().show();
			}
			else
			{
				t.addClass('sc_dbg_disabled');
				t.next().hide();
			}
		}
	},
	'.sc_dbg td:not(.sc_dbg_title)'
);
