/*global define */
define([
    'handlebars',
    'jquery',
    'views/modal-view',
    'text!templates/property.html'
], function (
    Handlebars,
    $,
    ModalView,
    propertyTemplate
) {
    'use strict';
    /**
     * View of a single property on a record
     * @constructor
     * @param {string} options.model - instance of a PropertyModel
     * @param {object} options.$el - container Element object
     * for this view
     */
    var PropertyView = function(options) {
        this.initialize.apply(this, [options]);
    };

    $.extend(PropertyView.prototype, {
        initialize: function(options) {
            this.model = options.model;
            this.$el = options.$el;
            this.deleteModalView = undefined;
            this.timeoutId = undefined;
            // subscribe to model events
            this.model.Observer('loadDataSuccess').subscribe(
                this.render.bind(this)
            );
            this.model.Observer('changeCurrentItem').subscribe(
                this.changeValueHandler.bind(this)
            );
        },

        /** Compile the template we will use to render the View */
        template: Handlebars.compile(propertyTemplate),

        /** Compile the template we will use to render 'url' values */
        anchorTemplate: Handlebars
            .compile('<a href="{{ value }}">{{ value }}</a>'),

        /** Compile the template we will use to render 'image' values */
        imageTemplate: Handlebars
            .compile('<img src="{{ value }}" style="height: 50px" />'),

        /** Compile the default template for values */
        textTemplate: Handlebars.compile('{{ value }}'),

        /** Event handler when a .name input is changed */
        changeLabelHandler: function(event) {
            clearTimeout(this.timeoutId);
            this.timeoutId = setTimeout(function() {
                this.model.label = event.target.value;
                return this.model.updateProperty();
            }.bind(this), 600);
        },

        /** Event handler when a .types input is changed */
        changeTypeHandler: function(event) {
            var newType = $(event.target).find(':selected').val();
            this.model.type = newType;
            this.renderValue();
            return this.model.updateProperty();
        },

        /** Event handler for when the current record (value) changes */
        changeValueHandler: function() {
            this.renderValue();
            return false;
        },

        /** Event handler for when the delete button is clicked */
        showDeleteModalHandler: function() {
            this.deleteModalView = new ModalView({
                header: 'Delete "' + this.model.label + '"?',
                body: '<div class="alert alert-warning"> ' +
                    '<strong>Warning:</strong> This data will be deleted ' +
                    'and cannot be recovered. Are you sure you want to ' +
                    'delete this property?</div>',
                buttonText: 'Delete Property',
                buttonFunction: this.deleteProperty.bind(this)
            });
            this.deleteModalView.$el.on('hide.bs.modal', function () {
                this.destroy();
            }.bind(this.deleteModalView));
            this.deleteModalView.render();
            this.deleteModalView.$el.modal('show');
            return false;
        },

        /** Re-render the value of the PropertyModel */
        renderValue: function() {
            var animateDuration = 200;
            var valueType = this.$el.find(':selected').val();
            var valueEl = this.$el.find('.value');
            valueEl.fadeOut(animateDuration, function() {
                // change rendering for this.model.value on certain types
                if (valueType === 'image') {
                    valueEl.html(this.imageTemplate({value: this.value()}));
                } else if (valueType === 'url') {
                    valueEl.html(this.anchorTemplate({value: this.value()}));
                } else {
                    valueEl.html(this.textTemplate({value: this.value()}));
                }
                valueEl.fadeIn(animateDuration);
            }.bind(this));
        },

        /** Add this view to the DOM */
        render: function() {
            this.$el.html(this.template({
                id: this.model.id(),
                label: this.label(),
                type: this.type(),
                value: this.value(),
                selectedType: this.selectedType()
            }));
            // bind to DOM events
            this.$el.find('.name input').on(
                'input', this.changeLabelHandler.bind(this));
            this.$el.find('.types select').on(
                'change', this.changeTypeHandler.bind(this));
            this.$el.find('#delete-' + this.model.id()).on(
                'click', this.showDeleteModalHandler.bind(this));
            return this;
        },

        /** Shortcut to PropertyModel.label for easy templating */
        label: function() { return this.model.label; },

        /** Shortcut to PropertyModel.type for easy templating */
        type: function() { return this.model.type; },

        /** Shortcut to PropertyModel.currentItem for easy templating */
        value: function() { return this.model.currentItem().value; },

        /** Our logic-less templates use this to mark
         * a 'type' <option> as selcted */
        selectedType: function() {
            var selected = {
                text: false,
                url: false,
                image: false,
                date: false,
                location: false,
                number: false
            };
            selected[this.type()] = true;
            return selected;
        },

        /** Delete this.model and call destroy */
        deleteProperty: function() {
            var animateDuration = 200;
            this.deleteModalView.$el.modal('hide');
            this.$el.hide(animateDuration);
            this.model.deleteProperty();
            this.destroy();
        },

        /** Remove event bindings, child views, and DOM elements */
        destroy: function() {
            var inputs = this.$el.find('.name input');
            var types = this.$el.find('.types select');
            var deleteBtn = this.$el.find('#delete-' + this.model.id());
            inputs.off('change');
            types.off('change');
            deleteBtn.off('click');
            this.model.Observer('changeCurrentItem')
                .unsubscribe(this.changeValueHandler);
            this.$el.empty();
        }
    });

    return PropertyView;
});
